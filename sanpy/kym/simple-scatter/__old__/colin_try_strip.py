import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

data = [
    ["test1", 1.0, "Cat", "male"],
    ["test2", 1.5, "Cat", "male"],
    ["test3", 1.2, "Cat", "female"],
    ["test4", 1.1, "Cat", "female"],
    ["test5", 3.5, "Dog", "female"],
    ["test6", 2.2, "Dog", "male"],
    ["test7", 2.1, "Dog", "male"],
    ["test8", 2.3, "Dog", "female"],
    ["test9", 2.0, "Dog", "male"],
    ["test10", 2.15, "Dog", "female"],
    ["test11", 0.5, "Duck", "female"],
    ["test12", 0.4, "Duck", "male"],
    ["test13", 0.6, "Duck", "female"],
]
df = pd.DataFrame(data, columns=["name", "Size", "Animal", "Label"])
df.set_index("name", inplace=True)

print(df)

def onpick(event):
    name = df[df["Label"] == event.artist.label][
        df["Animal"] == event.artist.animal
    ].iloc[event.ind]
    print("Found:", name)


axes = sns.stripplot(x="Animal", y="Size", hue="Label", data=df, picker=4, dodge=True)
groups = df["Label"].unique()
splits = df["Animal"].unique()
print(axes.collections)
group_len = len(groups)
for idx, artist in enumerate(axes.collections):
    artist.animal = splits[idx // group_len]
    artist.label = groups[idx % group_len]
    print(artist.animal, artist.label)
axes.figure.canvas.mpl_connect("pick_event", onpick)
plt.show()