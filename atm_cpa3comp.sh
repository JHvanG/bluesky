#!/bin/bash
#SBATCH --time=6-00:00:00
#SBATCH --mem=10G
#SBATCH --nodelist=node49
#SBATCH --partition=regular
#SBATCH --mail-type=FAIL,END
#SBATCH --mail-user=j.h.van.gelder.1@student.rug.nl
 
module purge
module load Python/3.9.6-GCCcore-11.2.0

source /scratch/$USER/.envs/bluesky/bin/activate
 
python3 --version
which python3
python3 BlueSky.py --scenfile=dqn_relative.scn --headless --approaches=3 --reward=CPA --batch=32 --buffer=1000000