#!/usr/bin/env python

"""Code for analysing benchmark runs"""

import os
import os.path
import json
import collections
import time
import subprocess
import copy

import util.file


def _is_str(obj):
    """Test if obj is a string type, in a python2/3 compatible way.
    From https://stackoverflow.com/questions/4232111/stringtype-and-nonetype-in-python3-x
    """
    try:
        return isinstance(obj, basestring)
    except NameError:
        return isinstance(obj, str)

def _pretty_print_json(json_dict):
    """Return a pretty-printed version of a dict converted to json, as a string."""
    return json.dumps(json_dict, indent=4, separators=(',', ': '))

def _run(cmd):
    print('running command: ', cmd)
    beg_time = time.time()
    subprocess.check_call(cmd, shell=True)
    print('command succeeded in {}s: {}'.format(time.time()-beg_time, cmd))

def _run_get_output(cmd):
    print('running command: ', cmd)
    beg_time = time.time()
    output = subprocess.check_output(cmd, shell=True)
    print('command succeeded in {}s: {}'.format(time.time()-beg_time, cmd))
    return output

def _run_get_json(cmd):
    return json.loads(_run_get_output(cmd).strip())


def analyze_workflows():
    bam2analyses = collections.defaultdict(list)
    stats = collections.Counter()
    for analysis in os.listdir('runs'):
        def _file(name): return os.path.join('runs', analysis, name)
        if not os.path.isfile(_file('cromwell_execution_metadata.json')):
            stats['no_metadata'] += 1
            continue
        mdata = json.loads(util.file.slurp_file(_file('cromwell_execution_metadata.json')).strip())
        if not mdata['workflowName'].startswith('assemble_denovo'):
            stats['wrong_workflowName'] += 1
            continue
        if not mdata['status'] == 'Succeeded':
            stats['wrong_status'] += 1
            continue
        stats['considered'] += 1
        mdata = copy.deepcopy(mdata)
        mdata['analysis_id'] = analysis
        bam = mdata['inputs']['assemble_denovo.reads_unmapped_bam']
        bam2analyses[bam].append(mdata)
        print(analysis)
    print(stats)
    for bam, mdatas in bam2analyses.items():
        if len(mdatas) > 1:
            print('bam=', bam, 'analyses=', '\n'.join(map(str, [mdata['analysis_id'] for mdata in mdatas])))

            def canonicalize_val(v, analysis_id):
                if not _is_str(v): return v
                orig_v = v
                v = os.path.join('runs', analysis_id, v)
                if _is_str(v) and os.path.islink(v) and os.path.lexists(v) and '.git/annex/objects' in os.path.realpath(v):
                    return os.path.basename(os.path.realpath(v))
                #print('not canon: ', v)
                return orig_v

            for i in range(len(mdatas)):
                for j in range(i+1, len(mdatas)):
                    if mdatas[i]['outputs']['assemble_denovo.refine_2x_and_plot.assembly_length_unambiguous'] == \
                       mdatas[j]['outputs']['assemble_denovo.refine_2x_and_plot.assembly_length_unambiguous']: continue
                    print('COMPARING ', mdatas[i]['analysis_id'], mdatas[j]['analysis_id'])
                    def show_diff(which):
                        def get_items(mdata):
                            analysis_id = mdata['analysis_id']
                            mdata = mdata[which]
                            mdata = {k: canonicalize_val(v, analysis_id) for k, v in mdata.items()}
                            mdata = {k:v for k,v in mdata.items() if isinstance(v, (int, float)) or _is_str(v) and not v.startswith('SHA256')}
                            #print('canonicalized version', mdata)
                            return mdata
                        items_i = get_items(mdatas[i])
                        items_j = get_items(mdatas[j])
                        print('\n\n\n')
                        #print('KEYS', items_i.keys())
                        assert items_i.keys() == items_j.keys()
                        print('------------differing items {}----------', which)
                        for k in sorted(items_i.keys()):
                            if items_i[k] != items_j[k]:
                                print(k, items_i[k], items_j[k])
                        #print('\n'.join(sorted(map(str, items_i ^ items_j))))
                        print('--------end differing items {}-----------', which)
                        print('\n\n\n')
                    print('********* i={} j={}\n'.format(i,j))
                    show_diff('inputs')
                    show_diff('outputs')
                    print('***************************************')

if __name__ == '__main__':
    analyze_workflows()
