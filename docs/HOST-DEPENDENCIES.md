# Ubuntu 24.04 x86-64 host inputs

These are the user-space tools used to bootstrap the recorded reproduction.
Use their upstream releases; their package licenses and notices apply.

| Tool | Version / provenance | SHA-256 of tested executable |
|---|---|---|
| uv | Astral `0.12.21` x86_64-unknown-linux-gnu, MIT/Apache-2.0 | `e8a4e7b4fd6283892fccfc4f335fb16cdf01064bb135172e4e2e73b478eb2076` |
| micromamba | conda-forge `2.10.0` Linux x86-64, BSD-3-Clause | `701f39c06f8e6a670a0e186c8479b9e5c0502a2f0cda6cef65d83bdd2875e8bd` |
| hf | `huggingface-hub` CLI `2.4.0`, Apache-2.0, see the Comfy environment lock | Managed by the pinned Python environment |

Ubuntu Noble `libespeak-ng1` and `espeak-ng-data` were
`1.51+dfsg-12build1`. The downloaded same-version `espeak-ng` executable package
is verified in `bin/run-rehearsal`. eSpeak NG’s Debian copyright notice is in
`/usr/share/doc/libespeak-ng1/copyright`. The system shared library stays out
of Git and its tested SHA-256 was
`a18be542512749ea11dcbb5799f0de86a4bcacc75b3a625198160f67bfd37508`.

Install Ubuntu `fonts-noto-core` `20201225-2` (SIL OFL-1.1) for frame text
and `fonts-dejavu-core` `2.37-8` (DejaVu/Bitstream Vera license) for captions and
fallback. The tested bold faces have SHA-256
`e83493c945848ecd4a9ad0f6d19164541a0d3e23a9c952304a00a46e00272ac5` and
`5c1247acef7f2b8522a31742c76d6adcb5569bacc0be7ceaa4dc39dd252ce895`.
The font packages own their respective Debian copyright notices.

This note records tested artifacts, not a required system-wide downgrade.
Use the isolated setup to qualify any other driver, packages, or host version.
