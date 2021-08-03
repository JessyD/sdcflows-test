'''
Inspired by:
https://github.com/nipreps/fmriprep/blob/674124ee80b3e2a8affddf005e910e4ca1c97cc0/fmriprep/workflows/bold/resampling.py#L483

'''
from pathlib import Path
from niworkflows.engine.workflows import LiterateWorkflow as Workflow
from niworkflows.interfaces.itk import MultiApplyTransforms
from nipype.pipeline import engine as pe
from niworkflows.interfaces.nilearn import Merge
from nipype.interfaces import utility as niu
from nipype.interfaces.io import DataSink
from niworkflows.interfaces.itk import MCFLIRT2ITK
from glob import glob
from nipype.interfaces.fsl import Split
'''
hmc_xforms ITKTransform file aligning each volume to ``ref_image``

'''

def _first(inlist):
    return inlist[0]


def init_apply_sdcflows(
        mem_gb,
        omp_nthreads,
        use_compression,
        name='apply_sdcflows'
):
    '''
    use_compression : :obj:`bool`
        Save registered BOLD series as ``.nii.gz``
    '''
    workflow = Workflow(name=name)
    # Create merge workflow
    inputnode = pe.Node(niu.IdentityInterface(fields=[
        'epi', 'affine', 'fieldwarp', 'motion_correction', 'name_source']),
        name='inputnode'
    )

    outputnode = pe.Node(
        niu.IdentityInterface(fields=['corrected_epi']),
        name='outputnode')

    merge_xforms = pe.Node(niu.Merge(3), name='merge_xforms',
                           run_without_submitting=True)

    interpolation = 'LanczosWindowedSinc'
    bold_transform = pe.Node(
        MultiApplyTransforms(interpolation=interpolation, float=True, copy_dtype=True),
        name='bold_transform', mem_gb=mem_gb * 3 * omp_nthreads, n_procs=omp_nthreads)


    merge = pe.Node(Merge(compress=use_compression), name='merge', mem_gb=mem_gb * 3)

    datasink = pe.Node(DataSink(), name='sinker')
    workflow.connect([
        (inputnode, merge_xforms, [
            ('fieldwarp', 'in2'),
            ('affine', 'in3'),
            ('motion_correction', 'in1')]),
        (inputnode, bold_transform, [('epi', 'input_image'),
                                     (('epi',  _first), 'reference_image')]),
        (inputnode, merge, [('name_source', 'header_source')]),
        (merge_xforms, bold_transform, [('out', 'transforms')]),
        (bold_transform, merge, [('out_files', 'in_files')]),
        (merge, outputnode, [('out_file', 'corrected_epi')]),
        (outputnode, datasink, [('corrected_epi', 'sdcorrected')]),
   ])

    return workflow


if __name__ == '__main__':
    # Using rl but might need to use lr
    motion_correction = str('/data/NIMH_scratch/fmriprep_sdcflows/wrk/sub-132118b/fmriprep_wf/'
                            'single_subject_132118b_wf/func_preproc_task_rest_acq_rl_run_01_wf/'
                            'bold_hmc_wf/fsl2itk/mat2itk.txt')
    motion_correction_mat = str('/data/NIMH_scratch/fmriprep_sdcflows/wrk/sub-132118b/fmriprep_wf/'
                             'single_subject_132118b_wf/func_preproc_task_rest_acq_rl_run_01_wf/'
                              'bold_hmc_wf/mcflirt/sub-132118_task-rest_acq-rl_run-01_bold_mcf.nii.gz.par')
    fieldwarp = str('/data/jdafflon/sdcflows_tests/test4_wk/test_unwarp_wf/coeff2epi_wf/coregister/transform_Warped.nii.gz')
    affine = str('/data/jdafflon/sdcflows_tests/test4_wk/test_unwarp_wf/coeff2epi_wf/coregister/transform0GenericAffine.mat')
    name_source = str('/data/HCP/hcp_test_bids/sub-132118b/func/sub-132118_task-rest_acq-rl_run-01_bold.nii.gz')
    epi_paths = Path('/data/jdafflon/pycharm/sdcflows-test/image_vols')
    epi = [epi_vol for epi_vol in glob(str(epi_paths / 'vol*.nii.gz'))]
    mem_gb = 3
    omp_nthreads = 1

    workflow = init_apply_sdcflows(mem_gb, omp_nthreads, use_compression=True)
    workflow.inputs.inputnode.epi = epi
    workflow.inputs.inputnode.affine = affine
    workflow.inputs.inputnode.fieldwarp = fieldwarp
    workflow.inputs.inputnode.motion_correction = motion_correction
    workflow.inputs.inputnode.name_source = name_source


    workflow.base_dir = str(Path('/data/jdafflon/sdcflows_tests'))
    workflow.write_graph(graph2use='exec', format='svg')
    workflow.run(plugin="Linear")