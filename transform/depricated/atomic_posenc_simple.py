# SOAP 3d-coordinate Positional Encodings
import torch
import numpy as np
import ase
from ase import Atoms
from dscribe.descriptors import SOAP
from torch_geometric.data import Data
import os

def soap_local(input_directory, output_directory):
    os.makedirs(output_directory, exist_ok=True)

    # Iterate over the .pt files in the directory
    for filename in os.listdir(input_directory):
        if filename.endswith('.pt'):
           # Load the PyTorch Geometric Data object
            file_path = os.path.join(input_directory, filename)
            data = torch.load(file_path)

            # Retrieve the atom coordinates and existing 'x' tensor
            atom_coords = data['atom_coords']
            features_x = data['x']
            num_atoms = len(atom_coords)

            # Initialize the SOAP descriptor
            soap = SOAP(species=["H"], periodic=False, r_cut=2.5, n_max=4, l_max=4, sigma=0.1)

            # Create an ASE Atoms object
            system = Atoms(numbers=np.ones(num_atoms), positions=atom_coords.numpy())

            # Calculate SOAP descriptor for each atom
            soap_descriptors = soap.create(system)

            # Ensure the SOAP descriptors are in the correct shape for concatenation
            soap_descriptors = torch.tensor(soap_descriptors, dtype=torch.float32)

            # Concatenate the SOAP descriptors with the 'x' tensor
            data['x'] = torch.cat((features_x, soap_descriptors), dim=1)

            # Delete the 'atom_coords' from the data
            del data['atom_coords']

            # Save the updated data object
            output_file_path = os.path.join(output_directory, filename)
            torch.save(data, output_file_path)

    print(f"All local SOAP descriptors calculated, appended to 'x' and saved to {output_directory}.")

if __name__ == "__main__":

    input_directory = '/content/drive/MyDrive/protein-DATA/sample-normalized'
    output_directory = '/content/drive/MyDrive/protein-DATA/sample-atomic-encoded'
    
    soap_local(input_directory, output_directory)
