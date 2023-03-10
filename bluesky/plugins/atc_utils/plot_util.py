import os
import csv
import seaborn as sns
import matplotlib.pyplot as plt

sns.color_palette('deep')


def loss_plot(data: list[list, list]):
    plt.figure(figsize=(10, 6), tight_layout=True)
    # plotting
    ax = sns.lineplot(x=data[0], y=data[1], linewidth=2.5)
    plt.show()


def reward_plot(rewards: list):
    plt.figure(figsize=(10, 6), tight_layout=True)
    # plotting
    ax = sns.lineplot(data=rewards, linewidth=2.5)
    plt.show()


def action_distribution(actions: dict):
    plt.figure(figsize=(10, 6), tight_layout=True)
    # plotting
    ax = sns.lineplot(data=actions, linewidth=2.5)
    plt.show()
    pass


def separation_loss_plot(conflicts: list, LoS: list):
    ratio = [i/j for i, j in zip(conflicts, LoS)]
    plt.figure(figsize=(10, 6), tight_layout=True)
    # plotting
    ax = sns.lineplot(data=ratio, linewidth=2.5)
    plt.show()
    pass


def avg_time(times: list):
    print(sum(times)/len(times))
    pass


if __name__ == "__main__":
    workdir = os.getcwd()
    path = os.path.join(workdir, "results/training_results/")
    file = path + "training_results_first_1000_every_5.csv"

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
        loss_epochs = [result['epoch'][x] for x in loss_indices]
        loss_plot([loss_epochs, loss_data])
        reward_plot(result['average reward'])
        action_distribution({'LEFT': result['action LEFT'], 'RIGHT': result['action RIGHT'], 'LNAV': result['action LNAV']})
        separation_loss_plot(result['conflicts'], result['LoS'])
        avg_time(result['duration'])

