import bluesky as bs

# Experiment settings
SAVE_RESULTS = False                     # boolean to dictate whether results are written to the csv
LOAD_WEIGHTS = False                    # boolean to dictate whether previous weights should be loaded
NUM_TRANS = bs.num_approaches           # either 2 or 3 transitions

EVAL_COOLDOWN = 4                       # cooldown to let action take effect before applying reward
EPISODE_LIMIT = 7500                    # limits the amount of episodes
TIME_LIMIT = 720                        # 1440 updates equates to approximately 2 hours of simulation time
CONFLICT_LIMIT = 20                     # NOTE: rather randomly selected (was set to 20)
TRAIN_INTERVAL = 1                      # the number of episodes before retraining the network (was set to 2)
TARGET_INTERVAL = 100                   # the number of episodes before updating the target network
BUFFER_SIZE = bs.buffer_size            # in Mnih approx 1/50 of total number of instructions (OG is 1,000,000)
BATCH_SIZE = bs.batch_size              # batch size (initial training was with 128)
# LOSS_FUNCTION = "mse"                 # the loss function is mse, but then this should be clipped
LOSS_FUNCTION = "huber"                 # huber loss is similar to clipping MSE and adds stability
REWARD_FUNCTION = bs.reward_function    # Reward function can be LNAV, CPA or SPARSE

# Validation variables
TRAIN_LENGTH = 50                       # number of episodes used for training
VALIDATION_LENGTH = 5                   # number of episodes for model validation

# Generation settings
VARYING_SPAWN = True if NUM_TRANS == 2 else False      # boolean to dictate whether there is randomness in the spawn of an aircraft
GEN_INTERVAL = 360.0 if NUM_TRANS == 2 else 190.0      # time (seconds) it takes between spawn calls (180 for 3 after one another or 360 for two on equal dist)

# DQN exploration parameters
MAX_EPSILON = 1.0                       # maximum for exploration parameter
MIN_EPSILON = 0.01                      # minimum for exploration parameter
EPSILON_DECAY = 0.002                   # decay per training sequence

# Agent action
HDG_CHANGE = 45.0                       # HDG change instruction deviates 15 degrees from original

# Separation constraints
SEP_REP_HOR = 7.5                       # report within 5 nm (was 3.5 nm)
SEP_REP_VER = 1500                      # report within 1500 ft
SEP_MIN_HOR = 2.5                       # 2.5 nm is min sep
SEP_MIN_VER = 1000                      # 1000 ft is min sep

# Conversion factors
FT_NM_FACTOR = 0.000164578834           # ft * factor converts to nm
M_FT_FACTOR = 3.280839895               # m * factor converts to feet
MS_KT_FACTOR = 1.94384449               # m/s * factor converts to kt

# Reward weights
CPA_PENALTY = -5                        # penalty for reducing the cpa to below minimum separation distance
LoS_PENALTY = -10                       # penalty for losing separation
SEP_REWARD = 10                         # reward for attaining separation
LNAV_REWARD = 1                         # reward for LNAV reward function that encourages following ones flightplan
