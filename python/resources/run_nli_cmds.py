import argparse
import sys
from pathlib import Path

def build_args():
    parser = argparse.ArgumentParser("Build an NLI from a target CSV file")
    parser.add_argument("-n", "--nli_lib_zip", required=True,
                        help="The path to the ZIP file containing the nuix_nli_lib")
    parser.add_argument("-g", "--row_generator", required=True,
                        help="The path to a Python file which has the row generator class")
    parser.add_argument("-p", "--evidence_processor", required=True,
                        help="The path to a Python file which processed the evidence.  The variables 'evidence_path', 'output_path' and 'debug_mode' will be injected into script prior to running.")
    parser.add_argument("-e", "--evidence", required=True,
                        help="The path to the evidence to collect into an NLI")
    parser.add_argument("-o", "--output", required=True,
                        help="The path to a directory to save the output NLI file.  The name of the NLI file should be created in the processor.")
    parser.add_argument("--debug", required=False, action="store_true", default=False,
                        help="Enable debug mode, which shows more output and doesn't delete temporary files")
    return parser.parse_args()

def add_lib_to_path(lib_path: str):
    if not Path.exists(Path(lib_path)):
        raise ValueError("The nuix_nli_lib.zip path does not exist")

    print("NLI Library:", lib_path)
    sys.path.append(lib_path)

def check_evidence(evidence: str):
    if not Path.exists(Path(evidence)):
        raise ValueError("The evidence path does not exist")

    print("Evidence:", evidence)

def check_output(output: str):
    output_path = Path(output)
    output_exists = output_path.exists() if output_path.is_dir() else output_path.parent.exists()

    if not output_exists:
        raise ValueError("The output path does not exist")

    print("Output:", output)


if __name__ == "__main__":
    app_args = build_args()
    add_lib_to_path(app_args.nli_lib_zip)

    generator_path = app_args.row_generator
    if not Path.exists(Path(generator_path)):
        raise ValueError("The row generator path does not exist")
    print("Row Generator:", generator_path)
    exec(open(generator_path).read(), globals(), locals())

    evidence_path = app_args.evidence
    output_file_path = app_args.output
    debug_mode = app_args.debug
    check_evidence(evidence_path)
    check_output(output_file_path)

    processor_path = app_args.evidence_processor
    if not Path.exists(Path(processor_path)):
        raise ValueError("The evidence processor path does not exist")
    print("Evidence Processor:", processor_path)
    exec(open(processor_path).read(), globals(), locals())




