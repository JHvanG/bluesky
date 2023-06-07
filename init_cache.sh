#!/bin/bash
#SBATCH --time=00:01:00
#SBATCH --partition=regular

module purge
module load Python/3.9.6-GCCcore-11.2.0

source /scratch/$USER/.envs/bluesky/bin/activate

python3 --version
which python3
python3 BlueSky.py