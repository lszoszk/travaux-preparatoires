#!/bin/bash
# The vision reader (Chandra OCR 2) on PLGrid's Athena (ACK Cyfronet), grant PLG/2026/020181: one A100 per array task, a vLLM
# server on the node, pipeline/hpc/chandra_client.py sending it the task's share of the queue. Resumable: a page already read in
# $OUT is skipped, so a task that ran out of time is simply submitted again.
#
#   sbatch --array=0-3 pipeline/hpc/athena_chandra.sbatch       (from $WORK, after pipeline/hpc/athena_setup.sh)
#   LIMIT=50 sbatch pipeline/hpc/athena_chandra.sbatch           a test: 50 pages
#   QUEUE=$WORK/chandra_queue_consistency.json sbatch ...         another queue (pipeline/hpc/make_queues.py writes both)
#   touch $OUT/chandra.STOP                                      stops every task after its current pages
#
# Partition and account checked on Athena on 21 Oct 2026 (`sinfo`, `hpc-grants`); the allocation runs 27 Oct 2026 to 26 Oct 2027.
#SBATCH --job-name=chandra
#SBATCH --partition=plgrid-gpu-a100
#SBATCH --account=plgtravaux2026-gpu-a100
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=16
#SBATCH --mem=64G
#SBATCH --time=24:00:00
#SBATCH --output=logs/chandra-%A_%a.log

set -euo pipefail
WORK=${WORK:-$PWD}
OUT=${OUT:-$WORK/results}
N=${SLURM_ARRAY_TASK_COUNT:-1}
K=${SLURM_ARRAY_TASK_ID:-0}
module load Python/3.10.4
source "$WORK/venv/bin/activate"
export HF_HOME=$WORK/hf HF_HUB_OFFLINE=1  # (the weights are fetched on the login node by athena_setup.sh)
# torch's compiler runs `nvcc --version` for a debug note and catches only a missing nvcc; on the GPU nodes something named nvcc
# on PATH is not executable (PermissionError, the engine stops: 27 Oct 2026). CUDA 12.8's bin first, without its libraries.
export PATH=/net/software/v1/software/CUDA/12.8.0/bin:$PATH
PORT=$((8000 + K))

# the model server: bf16 on one A100 (40 GB), its own process group so that the job's end takes it down
vllm serve datalab-to/chandra-ocr-2 --served-model-name chandra --dtype bfloat16 --max-model-len 16384 \
    --gpu-memory-utilization 0.90 --limit-mm-per-prompt '{"image": 1}' --port $PORT > "logs/vllm-${SLURM_JOB_ID}_$K.log" 2>&1 &
SERVER=$!
trap 'kill $SERVER 2>/dev/null || true' EXIT
for i in $(seq 360); do
    curl -sf http://localhost:$PORT/health > /dev/null && break
    kill -0 $SERVER 2>/dev/null || { tail -50 "logs/vllm-${SLURM_JOB_ID}_$K.log"; exit 1; }
    sleep 10
done
echo "server up after $((i * 10)) s"

# (23 h: no new page in the job's last hour)
python3 pipeline/hpc/chandra_client.py --queue "${QUEUE:-$WORK/chandra_queue_plgrid.json}" --raw "$WORK/raw" --out "$OUT" \
    --api http://localhost:$PORT/v1 --workers 32 --hours 23 --shard "$K/$N" ${LIMIT:+--limit $LIMIT}
