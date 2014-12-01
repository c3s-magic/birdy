"""
WPS command line client

see help:
$ birdy -h
"""

import logging

def execute(wps, args):
    inputs = []
    # TODO: this is probably not the way to do it
    for key in args.__dict__.keys():
        if not key in ['identifier', 'output']:
            inputs.append( (key, str( getattr(args, key) )) )
    # list of tuple (output identifier, asReference attribute)
    outputs = [(args.output, True)]
    execution = wps.execute(args.identifier, inputs, outputs)
    monitor(execution, download=False)

def monitor(execution, sleepSecs=3, download=False, filepath=None):
    """
    Convenience method to monitor the status of a WPS execution till it completes (succesfully or not),
    and write the output to file after a succesfull job completion.
    
    execution: WPSExecution instance
    sleepSecs: number of seconds to sleep in between check status invocations
    download: True to download the output when the process terminates, False otherwise
    filepath: optional path to output file (if downloaded=True), otherwise filepath will be inferred from response document
    
    """
    
    while execution.isComplete()==False:
        execution.checkStatus(sleepSecs=sleepSecs)
        print 'Execution status: %s' % execution.status
        
    if execution.isSucceded():
        if download:
            execution.getOutput(filepath=filepath)
        else:
            for output in execution.processOutputs:               
                if output.reference is not None:
                    print 'Output URL=%s' % output.reference
    else:
        for ex in execution.errors:
            print 'Error: code=%s, locator=%s, text=%s' % (ex.code, ex.locator, ex.text)

def is_complex_data(input):
    return 'ComplexData' in input.dataType
            
def parse_default(input):
    default = None
    if hasattr(input, 'defaultValue'):
        default = input.defaultValue
        if default is not None:
            if is_complex_data(input):
                # TODO: get default value of complex type
                default = None #input.defaultValue.mimeType
            else:
                default = str(input.defaultValue)
    return default

def parse_description(input):
    description = ''
    if hasattr(input, 'title') and input.title is not None:
        description = str(input.title)
    if hasattr(input, 'abstract'):
        description = description + ": " + str(input.abstract)
    default = parse_default(input)
    if is_complex_data(input):
        if len(input.supportedValues) > 0: 
            mime_types = ",".join([str(value.mimeType) for value in input.supportedValues])
            description = description + ", mime types=" + mime_types
    if default is not None:
        description = description + " (default: " + str(default) + ")"
    return description.encode(encoding='ascii')

def parse_type(input):
    # TODO: see https://docs.python.org/2/library/argparse.html#type
    if 'boolean' in input.dataType:
        parsed_type=type(True)
    elif 'integer' in input.dataType:
        parsed_type=type(1)
    elif 'float' in input.dataType:
        parsed_type=type(1.0)
    elif 'ComplexData' in input.dataType:
        parsed_type=type('http://')
    else:
        parsed_type=type('')
    return parsed_type

def parse_choices(input):
    choices = None
    if len(input.allowedValues) > 0 and not input.allowedValues[0] == 'AnyValue':
        choices = input.allowedValues
    return choices

def parse_required(input):
    required = True
    if input.minOccurs == 0:
        required = False
    return required

def parse_nargs(input):
    nargs = '?'
    if input.maxOccurs > 1:
        if input.minOccurs > 0:
            nargs = '+'
        else:
            nargs = '*'
    elif input.minOccurs == 1:
        nargs == 1
    return nargs

def parse_process_help(process):
    help = ''
    if hasattr(process, "title"):
        help = help + str(process.title) + ": "
    if hasattr(process, "abstract"):
        help = help + str(process.abstract)
    return help.encode(encoding='ascii')

def parse_wps_description(wps):
    description="{0}: {1}".format(
        wps.identification.title,
        wps.identification.abstract)

def create_parser(wps):
    """
    Generates commands to execute WPS processes on the command line.
    
    See Python argparse documentation:
    https://chase-seibert.github.io/blog/2014/03/21/python-multilevel-argparse.html
    https://docs.python.org/2/howto/argparse.html
    https://docs.python.org/2/library/argparse.html#module-argparse
    https://argparse.googlecode.com/svn/trunk/doc/parse_args.html
    """
    
    import argparse
    import sys

    parser = argparse.ArgumentParser(
        usage='''birdy [-h] <command> [<args>]''',
        description=parse_wps_description(wps),
        )
    subparsers = parser.add_subparsers(
        dest='identifier',
        title='command',
        description='valid subcommands',
        help='additional help'
        )
    for process in wps.processes:
        #process = wps.describeprocess(wps.processes[i].identifier)
        parser_process = subparsers.add_parser(
            process.identifier,
            #help=parse_process_help(process)
            )

        

    args = parser.parse_args(sys.argv[1:2])
    print 'Arguments:', args
    process = wps.describeprocess(args.identifier)
    parser_process = subparsers.add_parser(
        process.identifier,
        #help=parse_process_help(process)
        )

    for input in process.dataInputs:
        parser_process.add_argument(
            '--'+input.identifier,
            dest=input.identifier,
            #required=parse_required(input),
            #nargs=parse_nargs(input),
            #type=parse_type(input),
            #choices=parse_choices(input),
            #default=parse_default(input),
            action="store",
            #help=parse_description(input),
        )
    output_choices = [output.identifier for output in process.processOutputs]
    help_msg = "Output: "
    for output in process.processOutputs:
       help_msg = help_msg + str(output.identifier) + "=" + parse_description(output) + " (default: output)"
    parser_process.add_argument(
        '--output',
        dest="output",
        default="output",
        choices=output_choices,
        action="store",
        help=help_msg
    )
    args = parser.parse_args(sys.argv[1:])
    print 'Arguments:', args
    sys.exit(1)
        
    return parser

def main():
    from sys import exit
    logging.basicConfig(format='%(levelname)s:%(message)s', level=logging.ERROR)

    from os import environ 
    service = environ.get("WPS_SERVICE", "http://localhost:8094/wps")
    logging.debug('using wps %s', service)

    from owslib.wps import WebProcessingService
    try:
        wps = WebProcessingService(service, verbose=False, skip_caps=False)
    except:
        logging.exception('Could not access wps %s', service)
        exit(1)

    parser = create_parser(wps)
    args = parser.parse_args()
    execute(wps, args)

if __name__ == '__main__':
    main()
