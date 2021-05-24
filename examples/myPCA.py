"""
20201218
see: https://medium.com/@dmitriy.kavyazin/principal-component-analysis-and-k-means-clustering-to-visualize-a-high-dimensional-dataset-577b2a7a5fe2
"""

# Imports
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler

##%config InlineBackend.figure_format='retina'

# Load in the data
path = 'apTable.csv'
df = pd.read_csv(path)

# remove some columns
dropColList = ['Unnamed: 0', 'index', 'Condition', 'analysisname']
df = df.drop(columns=dropColList)

# convert categorical to codes
df['Region'] = df['Region'].astype('category')
df['Region'] = df['Region'].cat.codes

df['Sex'] = df['Sex'].astype('category')
df['Sex'] = df['Sex'].cat.codes

print(df)

# Standardize the data to have a mean of ~0 and a variance of 1
X_std = StandardScaler().fit_transform(df)

# Create a PCA instance: pca
numComponents = 3
pca = PCA(n_components=numComponents)
principalComponents = pca.fit_transform(X_std)

# Plot the explained variances
features = range(pca.n_components_)
plt.bar(features, pca.explained_variance_ratio_, color='black')
plt.xlabel('PCA features')
plt.ylabel('variance %')
plt.xticks(features)
plt.show()

# Save components to a DataFrame
PCA_components = pd.DataFrame(principalComponents)

#
# plot the first 2 PC
plt.scatter(PCA_components[0], PCA_components[1], alpha=.1, color='black')
plt.xlabel('PCA 1')
plt.ylabel('PCA 2')
plt.show()

#
# run k-means clustering on the 1st three PC
ks = range(1, 10)
inertias = []
for k in ks:
	# Create a KMeans instance with k clusters: model
    model = KMeans(n_clusters=k)

    # Fit model to samples
    model.fit(PCA_components.iloc[:,:3])

    # Append the inertia to the list of inertias
    inertias.append(model.inertia_)

plt.plot(ks, inertias, '-o', color='black')
plt.xlabel('number of clusters, k')
plt.ylabel('inertia')
plt.xticks(ks)
plt.show()
