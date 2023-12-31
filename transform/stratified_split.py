# Multi-label stratified split for train, val, test sets
import os
import torch
from iterstrat.ml_stratifiers import MultilabelStratifiedKFold

def stratified_split(input_directory, n_splits=8):
    # Define the path for saving indices
    indices_file_path = os.path.join(os.path.dirname(input_directory), f"{os.path.basename(input_directory)}_split_indices.pt")

    # Load all files in the input directory
    file_list = os.listdir(input_directory)

    # Extract labels for splitting purposes
    label_representations = []
    for file in file_list:
        data = torch.load(os.path.join(input_directory, file))
        label_indices = data.y.nonzero(as_tuple=True)[0]
        label_representations.append(tuple(sorted(label_indices.tolist())))

    # Convert label representations to a format suitable for MultilabelStratifiedKFold
    unique_labels = sorted(set(sum(label_representations, ())))
    label_to_index = {label: idx for idx, label in enumerate(unique_labels)}

    multilabel_format = torch.zeros(len(file_list), len(unique_labels))
    for i, labels in enumerate(label_representations):
        for label in labels:
            multilabel_format[i, label_to_index[label]] = 1

    # Use MultilabelStratifiedKFold for splitting
    mskf = MultilabelStratifiedKFold(n_splits=n_splits, shuffle=True, random_state=42)
    
    indices = list(mskf.split(multilabel_format, multilabel_format))
    
    # Combine validation indices of first 6 folds for training, use 7th for validation and 8th for testing
    train_indices = [idx for fold in indices[:6] for idx in fold[1]]
    valid_indices = indices[6][1]
    test_indices = indices[7][1]

    # Assign file names to train, validation, and test sets based on the split indices
    indices_dict = {
        'train': [file_list[idx] for idx in train_indices],
        'valid': [file_list[idx] for idx in valid_indices],
        'test': [file_list[idx] for idx in test_indices]
    }

    # Save indices to a .pt file
    torch.save(indices_dict, indices_file_path)

    for key in indices_dict.keys():
        print(f"{key}: {len(indices_dict[key])} files")

if __name__ == "__main__":
    
    input_directory = '/content/drive/MyDrive/protein-DATA/sample-final'
    
    indices_dict = stratified_split(input_directory)
