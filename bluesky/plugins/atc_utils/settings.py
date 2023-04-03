
# Experiment settings
SAVE_RESULTS = False             # boolean to dictate whether results are written to the csv
EVAL_COOLDOWN = 4               # cooldown to let action take effect before applying reward
EPISODE_LIMIT = 4000            # limits the amount of episodes
TIME_LIMIT = 720                # 1440 updates equates to approximately 2 hours of simulation time
CONFLICT_LIMIT = 50             # NOTE: rather randomly selected
TRAIN_INTERVAL = 2              # the number of episodes before retraining the network
TARGET_INTERVAL = 100           # the number of episodes before updating the target network

# DQN exploration parameters
MAX_EPSILON = 1.0               # maximum for exploration parameter
MIN_EPSILON = 0.05              # minimum for exploration parameter
EPSILON_DECAY = 0.005           # decay per training sequence

# Agent action
HDG_CHANGE = 45.0               # HDG change instruction deviates 15 degrees from original

# Separation constraints
SEP_REP_HOR = 5.0               # report within 5 nm (was 3.5 nm)
SEP_REP_VER = 1500              # report within 1500 ft
SEP_MIN_HOR = 3.0               # 3 nm is min sep
SEP_MIN_VER = 1000              # 1000 ft is min sep

# Conversion factors
FT_NM_FACTOR = 0.000164578834   # ft * factor converts to nm
M_FT_FACTOR = 3.280839895       # m * factor converts to feet
MS_KT_FACTOR = 1.94384449       # m/s * factor converts to kt
