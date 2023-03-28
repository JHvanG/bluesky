import os
import csv
import sys
import seaborn as sns
import matplotlib.pyplot as plt

sns.color_palette('deep')
sns.set_style('white')

workdir = os.getcwd()
path = os.path.join(workdir, "results/training_results/")

LINEWIDTH = 1.5


def loss_plot(data: list[list, list], filename: str):
    plt.figure(figsize=(10, 6), tight_layout=True)
    # plotting
    plt.grid()
    plt.axhline(y=0, linewidth=0.9, color="k")
    ax = sns.lineplot(x=data[0], y=data[1], linewidth=LINEWIDTH)
    plt.xlim(0)
    plt.ylim((min(0, min(data[1]) - 0.5), max(0, max(data[1]) + 0.5)))
    plt.title("Progression of loss through episodes")
    plt.xlabel("Episode")
    plt.ylabel("Loss")
    plt.savefig(filename + "_loss.pdf")


def reward_plot(rewards: list, filename: str):
    plt.figure(figsize=(10, 6), tight_layout=True)
    # plotting
    plt.grid()
    plt.axhline(y=0, linewidth=0.9, color="k")
    ax = sns.lineplot(data=rewards, linewidth=LINEWIDTH)
    plt.xlim(0)
    plt.ylim((min(0, min(rewards) - 0.5), max(0, max(rewards) + 0.5)))
    plt.title("Progression of rewards through episodes")
    plt.xlabel("Episode")
    plt.ylabel("Reward")
    plt.savefig(filename + "_reward.pdf")


def action_distribution(actions: dict, filename: str):
    plt.figure(figsize=(10, 6), tight_layout=True)
    # plotting
    plt.grid()
    plt.axhline(y=0, linewidth=0.9, color="k")
    ax = sns.lineplot(data=actions, linewidth=LINEWIDTH)
    plt.xlim(0)
    plt.ylim(0)
    plt.title("Action distribution through episodes")
    plt.xlabel("Episode")
    plt.ylabel("Count")
    plt.savefig(filename + "_action.pdf")
    pass


def separation_loss_plot(conflicts: list, los: list, filename: str):
    data = {"conflicts": conflicts, "LoS": los}
    plt.figure(figsize=(10, 6), tight_layout=True)
    # plotting
    plt.grid()
    plt.axhline(y=0, linewidth=0.9, color="k")
    ax = sns.lineplot(data=data, linewidth=LINEWIDTH)
    plt.xlim(0)
    plt.ylim(0)
    plt.title("Conflicts / loss of separation through episodes")
    plt.xlabel("Episode")
    plt.ylabel("conflict/LoS")
    plt.savefig(filename + "_separation.pdf")
    pass


def avg_time(times: list):
    print(sum(times)/len(times))
    pass


if __name__ == "__main__":
    if len(sys.argv) > 1:
        filename = sys.argv[1]
    else:
        print("no filename provided, using default")
        filename = "training_results_first_1000_every_5.csv"

    file = path + filename

    data = []

    with open(file) as f:
        csvreader = csv.reader(f)
        keys = next(csvreader)

        result = dict.fromkeys(keys)

        first = True

        for row in csvreader:

            if first:
                for key, item in zip(keys, row):
                    if item.isdigit():
                        result[key] = [int(item)]
                    else:
                        try:
                            result[key] = [float(item)]
                        except ValueError:
                            result[key] = [item]
                first = False
            else:
                for key, item in zip(keys, row):
                    if item.isdigit():
                        result[key].append(int(item))
                    else:
                        try:
                            result[key].append(float(item))
                        except ValueError:
                            result[key].append(item)

        loss_indices = [i for i, j in enumerate(result['loss']) if j != ""]
        loss_data = [result['loss'][x] for x in loss_indices]
        loss_episodes = [result['episode'][x] for x in loss_indices]

        actions = {'LEFT': result['action LEFT'], 'RIGHT': result['action RIGHT'], 'LNAV': result['action LNAV']}

        fig_filename = file.strip(".csv")

        loss_plot([loss_episodes, loss_data], fig_filename)
        reward_plot(result['average reward'], fig_filename)

        action_distribution(actions, fig_filename)
        separation_loss_plot(result['conflicts'], result['LoS'], fig_filename)
        avg_time(result['duration'])

