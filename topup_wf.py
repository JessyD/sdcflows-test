from nipype.interfaces.utility import IdentityInterface
from sdcflows.workflows.fit.pepolar import init_topup_wf
from nipype.interfaces.fsl import ApplyTOPUP
from nipype.pipeline import engine as pe
import json
from sdcflows.workflows.outputs import init_fmap_derivatives_wf, init_fmap_reports_wf

blip_up = '/data/HCP/hcp_test_bids/sub-132118/fmap/sub-132118_dir-1_epi.nii.gz'
blip_down = '/data/HCP/hcp_test_bids/sub-132118/fmap/sub-132118_dir-2_epi.nii.gz'
blip_up_metadata = '/data/HCP/hcp_test_bids/sub-132118/fmap/sub-132118_dir-1_epi.json'
blip_down_metadata = '/data/HCP/hcp_test_bids/sub-132118/fmap/sub-132118_dir-2_epi.json'
in_data = [blip_up, blip_down]
with open(blip_up_metadata, 'r') as header:
    blip_up_dic = json.load(header)
with open(blip_down_metadata, 'r') as header:
    blip_down_dic = json.load(header)
metadata = [blip_up_dic, blip_down_dic]

base_dir = 'sdc_output2'
wf = pe.Workflow(name='Testsdc', base_dir=base_dir) 
topup_wf = init_topup_wf()
topup_wf.inputs.inputnode.in_data = in_data
topup_wf.inputs.inputnode.metadata = metadata

outdir = 'sdc_wf_output2'
fmap_derivatives_wf = init_fmap_derivatives_wf(output_dir=outdir, write_coeff=True, bids_fmap_id='pepolar_id')
fmap_derivatives_wf.inputs.inputnode.source_files = in_data
fmap_derivatives_wf.inputs.inputnode.fmap_meta = metadata

fmap_reports_wf = init_fmap_reports_wf(output_dir=outdir, fmap_type='pepolar')
fmap_reports_wf.inputs.inputnode.source_files = in_data

wf.connect([
	(topup_wf, fmap_reports_wf, [('outputnode.fmap', 'inputnode.fieldmap'),
				   	('outputnode.fmap_ref', 'inputnode.fmap_ref'),
					('outputnode.fmap_mask', 'inputnode.fmap_mask')]), 
	(topup_wf, fmap_derivatives_wf, [('outputnode.fmap', 'inputnode.fieldmap'),
               			         ('outputnode.fmap_ref', 'inputnode.fmap_ref'),
					 ('outputnode.fmap_coeff', 'inputnode.fmap_coeff')]),
 ])

wf.run(plugin='Linear')
wf.write_graph(graph2use='flat')
