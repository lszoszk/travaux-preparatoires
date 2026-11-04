#!/bin/bash
# One-time setup on Athena's login node (pipeline/hpc/athena_chandra.sbatch): a venv with vLLM and the client's few libraries,
# and the model weights, in $WORK (the group's storage; the compute nodes read the weights offline).
#
#   WORK=/path/on/the/group/storage bash pipeline/hpc/athena_setup.sh
set -euo pipefail
WORK=${WORK:?set WORK to the folder on the group storage}
cd "$WORK"
mkdir -p logs results hf
module load Python/3.10.4  # (the one Python module on Athena, 21 Oct 2026)
[ -d venv ] || python3 -m venv venv
source venv/bin/activate
pip install -q --upgrade pip
# the vLLM of the Kaggle runs (0.31.0, CUDA 12.9 build: Chandra OCR 2 is a Qwen3.5 model and needs a recent vLLM)
pip install -q "https://github.com/vllm-project/vllm/releases/download/v0.31.0/vllm-0.31.0+cu129-cp38-abi3-manylinux_2_28_x86_64.whl" \
    openai pymupdf --extra-index-url https://download.pytorch.org/whl/cu129
# (PyPI's torchcodec 0.17.0 is a CUDA 13 build, needs libnvrtc.so.13 and stops `vllm serve` with an OSError; there is no cu129
# build of it, and it only decodes audio and video, which vLLM treats as optional: removed, 27 Oct 2026)
pip uninstall -y -q torchcodec
# (vLLM's kernel warmup imports MiniMax M3's Triton kernels for every model; under Athena's Python 3.10 inspect.getsource cannot
# read one of them, decorated with lambdas, and the engine stops. The warmup does nothing for a model without MiniMax M3's
# sparse attention, Chandra included: the import is guarded, 27 Oct 2026)
python3 - <<'EOF'
import pathlib, vllm
p = pathlib.Path(vllm.__file__).parent / "model_executor/warmup/kernel_warmup.py"
old = """    from vllm.model_executor.warmup.minimax_m3_msa_warmup import (
        minimax_m3_msa_warmup,
    )
"""
new = """    try:
        from vllm.model_executor.warmup.minimax_m3_msa_warmup import (
            minimax_m3_msa_warmup,
        )
    except AttributeError:  # (travaux, Athena: Python 3.10 cannot read a MiniMax M3 kernel's source)
        def minimax_m3_msa_warmup(worker):
            return None
"""
s = p.read_text()
if old in s:
    p.write_text(s.replace(old, new))
    print("patched", p)
EOF
# (huggingface_hub 1.x renamed huggingface-cli to hf; the old name only prints its help, 23 Oct 2026)
HF_HOME=$WORK/hf hf download datalab-to/chandra-ocr-2 > /dev/null
python3 -c "import vllm, fitz, openai; print('vllm', vllm.__version__, '| pymupdf', fitz.__doc__.split()[1])"
du -sh "$WORK/hf" "$WORK/venv"
