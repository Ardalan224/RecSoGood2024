# -*- coding: utf-8 -*-
"""ItemKNN_RecPack_ML100K_UserBasedSplit+10_Core_Pruning.ipynb

Automatically generated by Colab.

Original file is located at
    https://colab.research.google.com/drive/1dJP92cwtI8qliW9l3ZUyCR1n6Z4KuDvP
"""

# Install necessary libraries
!pip install recpack

import recpack.pipelines as pipelines
from recpack.scenarios import WeakGeneralization
from recpack.datasets import MovieLens100K
import numpy as np
import pandas as pd
from recpack.preprocessing.preprocessors import DataFramePreprocessor

# Set random seed for reproducibility
np.random.seed(42)


# Specify the path where the dataset should be saved
dataset_path = '/content/drive/MyDrive/Master Thesis/Dataset/ml-100k/u.data'

# Load the dataset into a DataFrame directly
column_names = ['user_id', 'item_id', 'rating', 'timestamp']
ratings = pd.read_csv(dataset_path, sep='\t', names=column_names, usecols=['user_id', 'item_id', 'rating'])

print(len(ratings))

# Rename columns to match RecPack expectations
ratings = ratings.rename(columns={'reviewerID': 'user_id', 'asin': 'item_id', 'overall': 'rating'})
ratings = ratings.dropna(subset=['rating'])

# Inspect the ratings data
print("Initial Ratings Data Inspection:")
print("Number of interactions:", len(ratings))
print("Number of unique users:", ratings['user_id'].nunique())
print("Number of unique items:", ratings['item_id'].nunique())

# Check for users and items with fewer than 10 interactions
user_counts = ratings['user_id'].value_counts()
item_counts = ratings['item_id'].value_counts()

print("\nUsers with fewer than 10 interactions:", (user_counts < 10).sum())
print("Items with fewer than 10 interactions:", (item_counts < 10).sum())

# Check for empty rows
empty_rows = ratings.isnull().sum().sum()
print("\nNumber of empty rows:", empty_rows)

# Check for duplicate rows
duplicate_rows = ratings.duplicated().sum()
print("Number of duplicate rows:", duplicate_rows)
# Check for duplicate ratings (same user, same item)
duplicate_ratings = ratings.duplicated(subset=['user_id', 'item_id']).sum()
print("Number of duplicate ratings (same user, same item):", duplicate_ratings)

# Remove duplicate rows
ratings = ratings.drop_duplicates()
# Aggregate duplicate ratings (same user, same item) by averaging their ratings
ratings = ratings.groupby(['user_id', 'item_id'], as_index=False)['rating'].mean()

# Check for empty rows after cleaning
empty_rows = ratings.isnull().sum().sum()
print("\nNumber of empty rows after cleaning:", empty_rows)

# Check for duplicate rows after cleaning
duplicate_rows = ratings.duplicated().sum()
print("Number of duplicate rows after cleaning:", duplicate_rows)

# Check for duplicate ratings (same user, same item) after cleaning
duplicate_ratings = ratings.duplicated(subset=['user_id', 'item_id']).sum()
print("Number of duplicate ratings (same user, same item) after cleaning:", duplicate_ratings)

print(len(ratings))

# 10-core pruning
def prune_10_core(data):
    while True:
        # Filter users with fewer than 10 interactions
        user_counts = data['user_id'].value_counts()
        valid_users = user_counts[user_counts >= 10].index
        data = data[data['user_id'].isin(valid_users)]

        # Filter items with fewer than 10 interactions
        item_counts = data['item_id'].value_counts()
        valid_items = item_counts[item_counts >= 10].index
        data = data[data['item_id'].isin(valid_items)]

        # Check if no more pruning is needed
        if all(user_counts >= 10) and all(item_counts >= 10):
            break
    return data
# Apply 10-core pruning
ratings = prune_10_core(ratings)

print(len(ratings))

# Save the preprocessed DataFrame to a new CSV file
preprocessed_file_path = '/content/drive/MyDrive/Master Thesis/Dataset/ml-100k/preprocessed_ratings(for_RecPack).csv'
ratings.to_csv(preprocessed_file_path, index=False)

# Create an instance of MovieLens100K with the preprocessed file
class CustomMovieLens100K(MovieLens100K):
    def _load_dataframe(self):
        return pd.read_csv(preprocessed_file_path)

# Preprocess the data using RecPack
proc = DataFramePreprocessor(item_ix='item_id', user_ix='user_id')
# Process the DataFrame to get the interaction matrix
interaction_matrix = proc.process(ratings)

# Print the number of interactions, users, and items before splitting
print("Number of interactions in the original set:", interaction_matrix.num_interactions)
print("Number of unique users in the original set:", len(interaction_matrix.active_users))
print("Number of unique items in the original set:", len(interaction_matrix.active_items))

# Check and remove empty rows (users with no interactions) and empty columns (items with no interactions)
# This should not change anything due to the 10-core filtering already applied
interaction_matrix = interaction_matrix.users_in(interaction_matrix.active_users)
interaction_matrix = interaction_matrix.items_in(interaction_matrix.active_items)

# Print the number of interactions, users, and items after ensuring no empty rows or columns
print("Number of interactions after ensuring no empty rows or columns:", interaction_matrix.num_interactions)
print("Number of unique users after ensuring no empty rows or columns:", len(interaction_matrix.active_users))
print("Number of unique items after ensuring no empty rows or columns:", len(interaction_matrix.active_items))

# Define the WeakGeneralization scenario with 20% of the data for testing+validation (The fraction value is slightly different since due to the fact that the splitting procedure rounds up the values,
# therefore the split ratio won't be exactly 80-20 anymore, so I adjusted the split ratio manually to make sure the 80-20 ratio is correctly maintained)
# 0.205
test_valid_fraction = 0.205
weak_gen_scenario = WeakGeneralization(frac_data_in=1 - test_valid_fraction, validation=False, seed=42)

# Split the data
weak_gen_scenario.split(interaction_matrix)

# Use attributes to get the train+validation and test sets
train_interactions = weak_gen_scenario.full_training_data
test_valid_interactions = weak_gen_scenario.test_data_out

print("Number of interactions in train set:", train_interactions.num_interactions)
print("Number of interactions in test_valid set:", test_valid_interactions.num_interactions)

print("Number of unique users in training set:", len(train_interactions.active_users))
print("Number of unique items in training set:", len(train_interactions.active_items))

# Splitting test_valid set from each other (Again, fraction value is slightly different to maintatin the 50-50 split ration in this case correctly (due to rounding up effect))
# 0.48
test_valid_scenario = WeakGeneralization(frac_data_in=0.48, validation=False, seed=42)

# Split the data
test_valid_scenario.split(test_valid_interactions)

# Use attributes to get the train+validation and test sets
valid_interactions = test_valid_scenario.full_training_data
test_out_interactions = test_valid_scenario.test_data_out
print("Number of interactions in valid set:", valid_interactions.num_interactions)
print("Number of interactions in test set:", test_out_interactions.num_interactions)
print("Number of unique users in validation set:", len(valid_interactions.active_users))
print("Number of unique items in validation set:", len(valid_interactions.active_items))
print("Number of unique users in test set:", len(test_out_interactions.active_users))
print("Number of unique items in test set:", len(test_out_interactions.active_items))



# Downsampling training set (Again, fraction value is different to maintatin the 50-50 split ration in this case correctly (due to rounding up effect))
# Amazon_Toys and Games:  10% = 0.094....20% = 0.194....30% = 0.294....40% = 0.394....50% = 0.495....60% = 0.594....70% = 0.694....80% = 0.794....90% = 0.894...100% = 1.0
downsample_fraction = 1.0
additional_split_scenario = WeakGeneralization(frac_data_in=downsample_fraction, validation=False, seed=42)
additional_split_scenario.split(train_interactions)

# Downsampled train+validation set
downsampled_train_interactions = additional_split_scenario.full_training_data
print("Number of interactions in downsampled training set:", downsampled_train_interactions.num_interactions)
print("Number of unique users in training set:", len(downsampled_train_interactions.active_users))
print("Number of unique items in training set:", len(downsampled_train_interactions.active_items))

# Construct pipeline_builder and add data
pipeline_builder = pipelines.PipelineBuilder('ML100K')

# Set data (Each already splitted set in previous scenarios is used in its correct parameter position here based on the RecPack documentation for setting your own sets in the pipeline)
# full_training_data = downsampled_train_interactions, test_data_in = downsampled_train_interactions, test_data_out = test_out_interactions, validation_training_data = downsampled_train_interactions,
# validation_data_in = downsampled_train_interactions, validation_data_out = valid_interactions
pipeline_builder.set_full_training_data(downsampled_train_interactions)
pipeline_builder.set_test_data((downsampled_train_interactions, test_out_interactions))
pipeline_builder.set_validation_training_data(downsampled_train_interactions)
pipeline_builder.set_validation_data((downsampled_train_interactions, valid_interactions))

# Add algorithm with hyperparameter ranges for optimization
pipeline_builder.add_algorithm(
    'ItemKNN',
    grid={
        'K': [1, 10, 15, 20, 30, 40, 50, 60, 70, 80, 90, 100, 150, 200,250, 300, 350, 375, 400, 425, 450, 500],  # Range of K values for optimization
    }
)

# Set NDCGK as the optimization metric to evaluate at K=10
pipeline_builder.set_optimisation_metric('NDCGK', K=10)

# Add NDCGK metric to be evaluated at K=10
pipeline_builder.add_metric('NDCGK', [10])

# Construct pipeline
pipeline = pipeline_builder.build()

# Run pipeline, will first do optimisation, and then evaluation
pipeline.run()

# Get the metric results
metric_results = pipeline.get_metrics()

# Print the metric results
print("Metric Results:")
print(metric_results)

# Print the best hyperparameters
print("Best Hyperparameters:")
print(pipeline.optimisation_results)