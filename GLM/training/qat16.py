#!/usr/bin/env python3
"""qat16.py - quantization-aware fine-tuning for the 16k class-G models.

Float val 0.39 -> int8 loss 4.5: per-row power-of-two int8 quantization
(the C engine's fixed RTLM format) rounds every weight, and with h1=6
each weight carries a large share of the function, so the packed models
answered in mush. Fix: fine-tune the float weights with the
quantize-dequantize operator in the forward pass (straight-through
estimator) plus the Q7 activation clip, so the weights settle into
values that survive rounding. All scales (a_e, per-row alpha+shift for
W1, per-row shift for Wo) are recomputed from calibration exactly the
way pack.py does, every 500 steps.

The deployed pipeline's exact float-equivalent (derived from
intsim.IntModel.from_float):

    x_eff   = qdq(E, a_e*128)                    # element-wise
    W1_eff  = qdq(W1, alpha*2^s1)                # per row, RAW W1
    z1      = [x_eff, 1] @ W1_eff.T
    h_eff   = clip(k1 * relu(z1), 0, 127/128)    # k1 = alpha * a_e
    Wo_mod  = Wo with hidden lanes / k1
    Wo_eff  = qdq(Wo_mod, 2^sho)                 # per row
    logits  = [h_eff, 1] @ Wo_eff.T

In the unsaturated regime this equals the plain float forward, so
fine-tuning here transfers 1:1 to the device.

Usage: python3 qat16.py <npz-in> <corpus> <npz-out> [steps] [lr]
"""
import sys

import numpy as np

sys.path.insert(0, "training")
from rtcharset import encode
from train import MLP, Adam
import intsim

CLIP_HI = 127.0 / 128.0


def qdq(W, scale):
    q = np.clip(np.round(W * scale[:, None]), -128, 127)
    return q / scale[:, None]


def build_scales(m, calib):
    """The exact pack.py scales for the current weights."""
    emax = float(np.abs(m.E).max())
    a_e = 0.99 / emax if emax > 0.99 else min(4.0, 0.99 / max(emax, 1e-4))
    Eq = np.clip(np.round(m.E * a_e * 128.0), -128, 127)
    X = Eq[calib].reshape(len(calib), -1)
    Xr = np.hstack([X / 128.0, np.ones((len(X), 1))])
    W1e = m.W1.copy()
    W1e[:, -1] *= a_e
    acc_f = Xr @ W1e.T
    rmax = np.maximum(acc_f.max(axis=0), 0.0)
    alpha = np.where(rmax > 0.94, 0.94 / np.maximum(rmax, 1e-9),
                     np.minimum(4.0, 0.94 / np.maximum(rmax, 1e-4)))
    alpha = np.where(rmax <= 0, 1.0, alpha)
    sc1 = np.array([
        float(1 << intsim.q_shift(float(np.abs(m.W1[o] * alpha[o]).max())))
        * alpha[o] for o in range(m.h1)])
    Wo_mod = m.Wo.copy()
    k1 = alpha * a_e
    Wo_mod[:, :-1] /= k1[None, :]
    sho = np.array([
        float(1 << intsim.q_shift(float(np.abs(Wo_mod[o]).max())))
        for o in range(len(m.Wo))])
    return a_e, sc1, sho, k1


def main():
    inp, corpus, outp = sys.argv[1], sys.argv[2], sys.argv[3]
    steps = int(sys.argv[4]) if len(sys.argv) > 4 else 4000
    lr = float(sys.argv[5]) if len(sys.argv) > 5 else 2e-4

    d = np.load(inp)
    m = MLP.__new__(MLP)
    m.E = d["E"].astype(np.float64)
    m.W1 = d["W1"].astype(np.float64)
    m.W2 = None
    m.Wo = d["Wo"].astype(np.float64)
    m.h1 = m.W1.shape[0]
    m.ctx = (m.W1.shape[1] - 1) // d["E"].shape[1]
    m.emb = d["E"].shape[1]

    data = np.array(encode(open(corpus).read()), dtype=np.int64)
    rng = np.random.default_rng(55)
    crng = np.random.default_rng(7)
    opt = Adam(m, lr)
    B = 128

    def scales():
        pos = crng.integers(0, len(data) - m.ctx - 1, size=256)
        calib = np.stack([data[p:p + m.ctx] for p in pos])
        return build_scales(m, calib)

    a_e, sc1, sho, k1 = scales()
    for step in range(1, steps + 1):
        if step % 500 == 0:
            a_e, sc1, sho, k1 = scales()
        pos = rng.integers(0, len(data) - m.ctx - 1, size=B)
        idx = np.stack([data[p:p + m.ctx] for p in pos])
        tgt = data[pos + m.ctx]

        # ---- forward: the deployed pipeline's float-equivalent ----
        Eeff = np.clip(np.round(m.E * a_e * 128.0), -128, 127) / (a_e * 128.0)
        W1eff = qdq(m.W1, sc1)
        Wo_mod = m.Wo.copy()
        Wo_mod[:, :-1] /= k1[None, :]
        Woeff = qdq(Wo_mod, sho)

        x = Eeff[idx].reshape(B, -1)
        one = np.ones((B, 1))
        z1 = np.hstack([x, one]) @ W1eff.T
        hk = np.maximum(z1, 0) * k1[None, :]
        hmask = (hk <= CLIP_HI)                     # Q7 saturation mask
        heff = np.clip(hk, 0, CLIP_HI)
        hb = np.hstack([heff, one])
        logits = hb @ Woeff.T

        # ---- loss + grads (STE through qdq and clip) ----
        z = logits - logits.max(axis=1, keepdims=True)
        ez = np.exp(z)
        p = ez / ez.sum(axis=1, keepdims=True)
        loss = -np.log(np.maximum(p[np.arange(B), tgt], 1e-9)).mean()
        dlog = p.copy()
        dlog[np.arange(B), tgt] -= 1.0
        dlog /= B

        gWomod = dlog.T @ hb                        # grad wrt Wo_mod (pre-qdq)
        dhb = dlog @ Woeff                          # STE through Wo qdq
        dheff = dhb[:, :-1]
        dhk = dheff * hmask                         # clip: 0 where saturated
        dz1 = dhk * k1[None, :] * (z1 > 0)          # hk = relu(z1)*k1
        gW1 = dz1.T @ np.hstack([x, one])           # STE through W1 qdq
        dx1 = dz1 @ W1eff
        gE = np.zeros_like(m.E)
        np.add.at(gE, idx, dx1[:, :-1].reshape(B, m.ctx, m.emb))
        gWo = gWomod.copy()                         # hidden lanes were /k1
        gWo[:, :-1] /= k1[None, :]
        opt.step(m, {"E": gE, "W1": gW1, "Wo": gWo})

        if step % 500 == 0 or step == 1:
            print(f"qat {step:5d} loss {loss:.4f}", flush=True)

    np.savez_compressed(outp, E=m.E.astype(np.float32),
                        W1=m.W1.astype(np.float32),
                        W2=np.zeros((1, 1), dtype=np.float32),
                        Wo=m.Wo.astype(np.float32))
    print("saved", outp)


if __name__ == "__main__":
    main()
