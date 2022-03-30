# CPU-Emulator with Transient Execution

[![pipeline status](https://git.cs.uni-bonn.de/boes/lab_transient_ws_2122/badges/main/pipeline.svg)](https://git.cs.uni-bonn.de/boes/lab_transient_ws_2122/-/commits/main)

## System Requirements and installation

The following things need to be installed to run the program:

- Python >= 3.8
- Python-Benedict
- Python-Prompt-Toolkit

To install the required packages, one may use the following command:

    pip install -r requirements.txt

## Running the program

The syntax for running the emulator from the root folder of the repository is:

    ./main.py <path_to_target_program>

On Windows systems, the following command should be used instead:

    python main.py <path_to_target_program>

There are demo programs available in the `demo` folder, including sample attacks using meltdown and spectre.

## Config

Edit `config.yml` to change the default settings.


## Further Information

For further information, check the accompanying document located in `docs/lab.pdf`.