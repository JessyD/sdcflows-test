"""Test unwarp."""
from pathlib import Path
from nipype.pipeline import engine as pe

from sdcflows.workflows.fit.fieldmap import init_magnitude_wf
from sdcflows.workflows.apply.correction import init_unwarp_wf
from sdcflows.workflows.apply.registration import init_coeff2epi_wf


def test_unwarp_wf(datadir, workdir, outdir):
    """Test the unwarping workflow."""
    distorted = (datadir / 'func/sub-132118_task-rest_acq-rl_run-01_bold.nii.gz')

    magnitude = (
        datadir / "fmap" / "sub-132118_run-01_magnitude2.nii.gz"
    )
    fmap_ref_wf = init_magnitude_wf(2, name="fmap_ref_wf")
    fmap_ref_wf.inputs.inputnode.magnitude = magnitude

    epi_ref_wf = init_magnitude_wf(2, name="epi_ref_wf")
    epi_ref_wf.inputs.inputnode.magnitude = distorted

    reg_wf = init_coeff2epi_wf(2, debug=True, write_coeff=True)
    # Note: This was generated using the other script in this repo (topup_wf.py)
    reg_wf.inputs.inputnode.fmap_coeff =\
    ['sdc_wf_output2/sdcflows/sub-132118/fmap/sub-132118_fmapid-pepolarid_desc-coeff_fieldmap.nii.gz']

    unwarp_wf = init_unwarp_wf(omp_nthreads=2, debug=True)
    unwarp_wf.inputs.inputnode.metadata = {
        "EffectiveEchoSpacing": 0.00058,
        "PhaseEncodingDirection": "i",
    }

    workflow = pe.Workflow(name="test_unwarp_wf")
    # fmt: off
    workflow.connect([
        (epi_ref_wf, unwarp_wf, [("outputnode.fmap_ref", "inputnode.distorted")]),
        (epi_ref_wf, reg_wf, [
            ("outputnode.fmap_ref", "inputnode.target_ref"),
            ("outputnode.fmap_mask", "inputnode.target_mask"),
        ]),
        (fmap_ref_wf, reg_wf, [
            ("outputnode.fmap_ref", "inputnode.fmap_ref"),
            ("outputnode.fmap_mask", "inputnode.fmap_mask"),
        ]),
        (reg_wf, unwarp_wf, [("outputnode.fmap_coeff", "inputnode.fmap_coeff")]),
    ])
    # fmt:on

    if outdir:
        from niworkflows.interfaces.reportlets.registration import (
            SimpleBeforeAfterRPT as SimpleBeforeAfter,
        )
        from sdcflows.workflows.outputs import DerivativesDataSink
        from sdcflows.interfaces.reportlets import FieldmapReportlet

        report = pe.Node(
            SimpleBeforeAfter(
                before_label="Distorted",
                after_label="Corrected",
            ),
            name="report",
            mem_gb=0.1,
        )
        ds_report = pe.Node(
            DerivativesDataSink(
                base_directory=str(outdir),
                suffix="bold",
                desc="corrected",
                datatype="figures",
     #           dismiss_entities=("fmap",),
                source_file=distorted,
            ),
            name="ds_report",
            run_without_submitting=True,
        )

        rep = pe.Node(FieldmapReportlet(apply_mask=True), "simple_report")
        rep.interface._always_run = True

        ds_fmap_report = pe.Node(
            DerivativesDataSink(
                base_directory=str(outdir),
                datatype="figures",
                suffix="bold",
                desc="fieldmap",
    #            dismiss_entities=("fmap",),
                source_file=distorted,
            ),
            name="ds_fmap_report",
        )

        # fmt: off
        workflow.connect([
            (epi_ref_wf, report, [("outputnode.fmap_ref", "before")]),
            (unwarp_wf, report, [("outputnode.corrected", "after"),
                                 ("outputnode.corrected_mask", "wm_seg")]),
            (report, ds_report, [("out_report", "in_file")]),
            (epi_ref_wf, rep, [("outputnode.fmap_ref", "reference"),
                               ("outputnode.fmap_mask", "mask")]),
            (unwarp_wf, rep, [("outputnode.fieldmap", "fieldmap")]),
            (rep, ds_fmap_report, [("out_report", "in_file")]),
        ])
        # fmt: on

    if workdir:
        workflow.base_dir = str(workdir)
    workflow.write_graph(graph2use='flat')
    workflow.run(plugin="Linear")

if __name__ == '__main__':
    datadir = Path('/data/HCP/hcp_test_bids/sub-132118')
    workdir = Path('test_wk')
    workdir.mkdir(parents=True, exist_ok=True)
    outdir = Path('test_out')
    outdir.mkdir(parents=True, exist_ok=True)

    test_unwarp_wf(datadir, workdir, outdir)
