# -*- coding: utf-8 -*-
"""FunkSVD(Updated_nDCG)_LensKit_ML100K_UserBasedSplit+10_Core_Pruning.ipynb

Automatically generated by Colab.

Original file is located at
    https://colab.research.google.com/drive/1csv52AjwSSfkcRbfaXrDRgq5R-zlqsvd
"""

!pip install lenskit

from lenskit import batch, topn, util
from lenskit import crossfold as xf
from lenskit.algorithms import Recommender
from lenskit.algorithms.funksvd import FunkSVD
import pandas as pd
from lenskit.datasets import ML100K
import seedbank

"""
Previous Behavior (Before Update):
Before the modification, the nDCG_LK class in LensKit used the following approach:

IDCG Calculation: It calculated the IDCG for the full list length n (i.e., IDCG@n), regardless of the number of items actually rated by the user.
Handling Fewer Rated Items: If fewer items than n were rated, it used the IDCG value computed for n (e.g., IDCG@10 for n=10) even if the user had only rated 5 items.
Example:

Suppose n = 10 and a user has only rated 5 items. The previous implementation would calculate IDCG@10, regardless of the fact that only 5 items were rated.
Updated Behavior (After Modification):
The updated nDCG_LK class now mimics RecPack’s behavior:

IDCG Calculation: It precomputes IDCG values up to n and uses these values based on the actual number of items rated (hist_len). If fewer items are rated than n, it directly uses the precomputed IDCG value for the number of rated items.
Handling Fewer Rated Items: If fewer items than n are rated, it uses the precomputed IDCG value for the exact number of rated items rather than for n.
Example:

Suppose n = 10 and a user has only rated 5 items. The updated implementation would use IDCG@5, not IDCG@10, because it directly refers to the precomputed IDCG value for 5 rated items.

Conclusion:
Previous Behavior: Always used IDCG@n, regardless of the actual number of rated items.
Updated Behavior: Uses IDCG@hist_len, where hist_len is the number of items actually rated by the user.
"""
import numpy as np

class nDCG_LK:
    def __init__(self, n, top_items, test_items):
        self.n = n
        self.top_items = top_items
        self.test_items = test_items

    def _ideal_dcg(self):
        iranks = np.zeros(self.n, dtype=np.float64)
        iranks[:] = np.arange(1, self.n + 1)
        idcg = np.cumsum(1.0 / np.log2(iranks + 1), axis=0)
        if len(self.test_items) < self.n:
            idcg[len(self.test_items):] = idcg[len(self.test_items) - 1]
        return idcg[self.n - 1]

    def calculate_dcg(self):
        dcg = 0
        for i, item in enumerate(self.top_items):
            if item in self.test_items:
                relevance = 1
            else:
                relevance = 0
            rank = i + 1
            contribution = relevance / np.log2(rank + 1)
            dcg += contribution
        return dcg

    def calculate(self):
        dcg = self.calculate_dcg()
        ideal_dcg = self._ideal_dcg()
        if ideal_dcg == 0:
            return 0
        ndcg = dcg / ideal_dcg
        return ndcg

# Initialize seed
seedbank.initialize(42)

# Load and preprocess the dataset
file_path = '/content/drive/MyDrive/Master Thesis/Dataset/ml-100k'
ml100k = ML100K(file_path)
ratings = ml100k.ratings

# Inspect the ratings data
print("Initial Ratings Data Inspection:")
print("Number of interactions:", len(ratings))
print("Number of unique users:", ratings['user'].nunique())
print("Number of unique items:", ratings['item'].nunique())

# Check for users and items with fewer than 10 interactions
user_counts = ratings['user'].value_counts()
item_counts = ratings['item'].value_counts()

print("\nUsers with fewer than 10 interactions:", (user_counts < 10).sum())
print("Items with fewer than 10 interactions:", (item_counts < 10).sum())

# Check for empty rows
empty_rows = ratings.isnull().sum().sum()
print("\nNumber of empty rows:", empty_rows)

# Check for duplicate rows
duplicate_rows = ratings.duplicated().sum()
print("Number of duplicate rows:", duplicate_rows)
# Check for duplicate ratings (same user, same item)
duplicate_ratings = ratings.duplicated(subset=['user', 'item']).sum()
print("Number of duplicate ratings (same user, same item):", duplicate_ratings)

# 10-core pruning
def prune_10_core(data):
    while True:
        # Filter users with fewer than 10 interactions
        user_counts = data['user'].value_counts()
        valid_users = user_counts[user_counts >= 10].index
        data = data[data['user'].isin(valid_users)]

        # Filter items with fewer than 10 interactions
        item_counts = data['item'].value_counts()
        valid_items = item_counts[item_counts >= 10].index
        data = data[data['item'].isin(valid_items)]

        # Check if no more pruning is needed
        if all(user_counts >= 10) and all(item_counts >= 10):
            break
    return data

# Apply 10-core pruning
ratings = prune_10_core(ratings)

# Inspect the pruned ratings data
print("\nAfter Pruning:")
print("Number of interactions:", len(ratings))
print("Number of unique users:", ratings['user'].nunique())
print("Number of unique items:", ratings['item'].nunique())

# Check for users and items with fewer than 10 interactions after pruning
user_counts = ratings['user'].value_counts()
item_counts = ratings['item'].value_counts()

print("\nUsers with fewer than 10 interactions after pruning:", (user_counts < 10).sum())
print("Items with fewer than 10 interactions after pruning:", (item_counts < 10).sum())

# Split into train and test sets
final_test_method = xf.SampleFrac(0.10, rng_spec=42)

train_parts = []
test_parts = []

for tp in xf.partition_users(ratings, 1, final_test_method):
    train_parts.append(tp.train)
    test_parts.append(tp.test)

train_data = pd.concat(train_parts)
final_test_data = pd.concat(test_parts)

# Split train data into train and validation sets
validation_split_method = xf.SampleFrac(0.1111, rng_spec=42)

train_parts = []
valid_parts = []

for tp in xf.partition_users(train_data, 1, validation_split_method):
    train_parts.append(tp.train)
    valid_parts.append(tp.test)

pure_train_data = pd.concat(train_parts)
validation_data = pd.concat(valid_parts)

# Check and print the number of interactions and users in each set
print("\nBefore Splitting:")
print("Pure Train Data - Number of Interactions:", len(pure_train_data))
print("Validation Data - Number of Interactions:", len(validation_data))
print("Final Test Data - Number of Interactions:", len(final_test_data))

print("Pure Train Data - Number of Users:", pure_train_data['user'].nunique())
print("Validation Data - Number of Users:", validation_data['user'].nunique())
print("Final Test Data - Number of Users:", final_test_data['user'].nunique())

# Downsample the training set to different% of interactions for each user using xf.SampleFrac
downsample_method = xf.SampleFrac(1.0 - 0.1, rng_spec=42)
downsampled_train_parts = []

for i, tp in enumerate(xf.partition_users(pure_train_data, 1, downsample_method)):
    downsampled_train_parts.append(tp.train)

# Combine downsampled train parts into one DataFrame
downsampled_train_data = pd.concat(downsampled_train_parts)

# Checks for number of interactions and users in each set after downsampling
print("\nAfter Downsampling:")
print("Downsampled Train Data - Number of Interactions:", len(downsampled_train_data))
print("Validation Data - Number of Interactions:", len(validation_data))
print("Final Test Data - Number of Interactions:", len(final_test_data))

print("Downsampled Train Data - Number of Users:", downsampled_train_data['user'].nunique())
print("Validation Data - Number of Users:", validation_data['user'].nunique())
print("Final Test Data - Number of Users:", final_test_data['user'].nunique())

def evaluate_with_ndcg(aname, algo, train, valid):
    fittable = util.clone(algo)
    fittable = Recommender.adapt(fittable)
    fittable.fit(train)
    users = valid.user.unique()
    recs = batch.recommend(fittable, users, 10)
    recs['Algorithm'] = aname

    total_ndcg = 0
    for user in users:
        user_recs = recs[recs['user'] == user]['item'].values
        user_truth = valid[valid['user'] == user]['item'].values
        ndcg_score = nDCG_LK(10, user_recs, user_truth).calculate()
        total_ndcg += ndcg_score

    mean_ndcg = total_ndcg / len(users)
    return recs, mean_ndcg

# Perform hyperparameter tuning on the validation set and compute nDCG (Other hyperparameters have alredy been tested and tuned for the best configuration)
results = []
best_features = None
best_iterations = None
best_mean_ndcg = -float('inf')
iteration_values = [1, 5, 10, 20, 50]
feature_values = [5, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100]  # Define a range of feature values to test

# Iterate over each iteration value and each feature value
for iterations in iteration_values:
    for features in feature_values:
        seedbank.initialize(42)  # Reset the random seed for reproducibility
        algo_funksvd = FunkSVD(features=features, iterations=iterations, lrate=0.001, reg=0.015, damping=0, bias=False, random_state=42)
        # Evaluate the model and compute mean nDCG
        valid_recs, mean_ndcg = evaluate_with_ndcg('FunkSVD', algo_funksvd, downsampled_train_data, validation_data)
        results.append({'Features': features, 'Iterations': iterations, 'Mean nDCG': mean_ndcg})

        # Check if the current combination is the best so far
        if mean_ndcg > best_mean_ndcg:
            best_mean_ndcg = mean_ndcg
            best_features = features
            best_iterations = iterations

print("Results:")
for result in results:
    print(f"Features = {result['Features']}, Iterations = {result['Iterations']}: Mean nDCG = {result['Mean nDCG']:.4f}")

print(f"\nBest Features: {best_features}, Best Iterations: {best_iterations} (Mean nDCG = {best_mean_ndcg:.4f})")

# Fit the algorithm on the full training data with the best features and iterations
final_algo = FunkSVD(features=best_features, iterations=best_iterations, lrate=0.001, reg=0.015, damping=0, bias=False, random_state=42)
# Use evaluate_with_ndcg to get recommendations and mean nDCG
final_recs, mean_ndcg = evaluate_with_ndcg('FunkSVD', final_algo, downsampled_train_data, final_test_data)

print(f"NDCG mean for test set: {mean_ndcg:.4f}")