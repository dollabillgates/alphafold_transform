# NetworkX > PyTorch Geometric Graph Representation of proteins
# with mirrored edges and PAE edges
import os
import torch
import networkx as nx
from sklearn import preprocessing
from collections import defaultdict
import pickle
from torch_geometric.data import Data
import numpy as np
import csv

input_dir = '/proteins_sample/'
output_dir = '/content/drive/MyDrive/protein-DATA/prot-sample/'
categories_path = '/content/drive/MyDrive/protein-DATA/ohe-categories.csv'

# Initialize OneHotEncoders for atom_name, atom_type, residue_name and secondary_structure
ohe_atom_names = preprocessing.OneHotEncoder(sparse_output=False)
ohe_atom_types = preprocessing.OneHotEncoder(sparse_output=False)
ohe_residue_names = preprocessing.OneHotEncoder(sparse_output=False)
ohe_secondary_structures = preprocessing.OneHotEncoder(sparse_output=False)

# Collect unique categorical values for each feature
unique_atom_names = set()
unique_atom_types = set()
unique_residue_names = set()
unique_secondary_structures = set()

# Iterate over all files in the input directory
for filename in os.listdir(input_dir):
    if filename.endswith(".pickle"):
        filepath = os.path.join(input_dir, filename)

        # Load the NetworkX graph
        with open(filepath, 'rb') as file:
            G = pickle.load(file)

        for node, data in G.nodes(data=True):
            unique_atom_names.add(data['atom_name'])
            unique_atom_types.add(data['atomic_number'])
            unique_residue_names.add(data['residue_name'])
            unique_secondary_structures.add(data['secondary_structure'])

# Fit the OneHotEncoders
ohe_atom_names.fit(np.array(list(unique_atom_names)).reshape(-1, 1))
ohe_atom_types.fit(np.array(list(unique_atom_types)).reshape(-1, 1))
ohe_residue_names.fit(np.array(list(unique_residue_names)).reshape(-1, 1))
ohe_secondary_structures.fit(np.array(list(unique_secondary_structures)).reshape(-1, 1))

# Write the unique categories to the file
with open(categories_path, 'w', newline='') as csvfile:
    category_writer = csv.writer(csvfile)
    category_writer.writerow(['atom_name'] + list(unique_atom_names))
    category_writer.writerow(['atom_type'] + list(unique_atom_types))
    category_writer.writerow(['residue_name'] + list(unique_residue_names))
    category_writer.writerow(['secondary_structure'] + list(unique_secondary_structures))

# Iterate over the files again to create and save PyG graphs
for filename in os.listdir(input_dir):
    if filename.endswith(".pickle"):
        data_object_name = filename.replace('.pickle', '')
        filepath = os.path.join(input_dir, filename)

        # Load the NetworkX graph
        with open(filepath, 'rb') as file:
            G = pickle.load(file)

            # Add mirrored edges if they do not exist
            for node1, node2, data in G.edges(data=True):
                if not G.has_edge(node2, node1):
                    G.add_edge(node2, node1, **data)

            # a dictionary to map node IDs to integers
            node_mapping = defaultdict(int)

            # Map node labels to integers
            for i, node in enumerate(G.nodes()):
                node_mapping[node] = i

            # Prepare features for edges
            edge_index = []
            edge_feat = []

            # Prepare node features
            feat = []

            # Prepare atom coordinates separately
            atom_coords_list = []

            for node, data in G.nodes(data=True):
                # Node features
                atom_coords = torch.tensor([float(i) for i in data['atom_coords'].split(",")])
                atom_coords_list.append(atom_coords)
                feat.append(torch.cat([torch.tensor(ohe_atom_names.transform([[data['atom_name']]])).squeeze(0),
                        torch.tensor(ohe_atom_types.transform([[data['atomic_number']]])).squeeze(0),
                        torch.tensor(ohe_residue_names.transform([[data['residue_name']]])).squeeze(0),
                        torch.tensor(ohe_secondary_structures.transform([[data['secondary_structure']]])).squeeze(0),
                        torch.tensor([[data['degree'],
                                      data['aromatic'],
                                      data['residue_number'],
                                      data['plddt'],
                                      data['exposure'],
                                      data['phi'],
                                      data['psi'],
                                      data['NH_O_1_relidx'],
                                      data['NH_O_1_energy'],
                                      data['O_NH_1_relidx'],
                                      data['O_NH_1_energy'],
                                      data['NH_O_2_relidx'],
                                      data['NH_O_2_energy'],
                                      data['O_NH_2_relidx'],
                                      data['O_NH_2_energy']]], dtype=torch.float).squeeze(0)
                    ], dim=0))


            for node1, node2, data in G.edges(data=True):
                # edge feature includes bond_idx, bond_order, bond_length and pae
                if 'pae' in data:
                    edge_feat.append([0, 0, 0, data.get('pae')])
                else:
                    edge_feat.append([
                        data.get('bond_idx', 0),
                        data.get('bond_order', 0),
                        data.get('bond_length', 0),
                        0])  # 0 for PAE in bond edges
                edge_index.append((node_mapping[node1], node_mapping[node2]))

            # Convert lists to tensors
            edge_index = torch.LongTensor(edge_index).t().contiguous()
            feat = torch.stack(feat)
            edge_feat = torch.tensor(edge_feat, dtype=torch.float)

            # Calculate geometric center and re-align atom_coords
            atom_coords_array = torch.stack(atom_coords_list)
            geometric_center = torch.mean(atom_coords_array, dim=0)
            aligned_atom_coords_list = [coords - geometric_center for coords in atom_coords_array]

            # Update atom_coords with the aligned coords
            atom_coords = torch.stack(aligned_atom_coords_list)

            # Create the num_nodes attribute
            num_nodes = feat.shape[0]
    
            # Construct the PyG graph
            data = Data(edge_index=edge_index, x=feat, edge_attr=edge_feat, num_nodes=num_nodes, atom_coords=atom_coords)
        
            # Save the PyTorch object to the local file system
            output_filename = f'{data_object_name}.pt'
            torch.save(data, os.path.join(output_dir, output_filename))
