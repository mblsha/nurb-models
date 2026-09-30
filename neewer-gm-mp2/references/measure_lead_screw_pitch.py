"""Look for reproducible axial periodicity before inventing a screw thread."""
import gzip
import hashlib
import io
import json
from pathlib import Path
import numpy as np
import trimesh

ROOT = Path(__file__).resolve().parents[1]
REFERENCE = ROOT / 'scans/neewer-macro-slide-GM-MP2.ply.gz'


def measure():
    body = REFERENCE.read_bytes()
    mesh = trimesh.load(io.BytesIO(gzip.decompress(body)), file_type='ply', process=False)
    reports = []
    for lo, hi in ((20.0, 70.0), (135.0, 185.0)):
        x = np.arange(lo, hi + .01, .2)
        radii = []
        for station in x:
            section = mesh.section(plane_origin=[station, 0, 0], plane_normal=[1, 0, 0])
            yz = section.vertices[:, 1:] - [22.0, 17.58]
            r = np.linalg.norm(yz, axis=1)
            r = r[r < 4.0]
            radii.append(np.percentile(r, [10, 50, 90]))
        radii = np.asarray(radii)
        series = []
        for index, label in enumerate(('p10', 'median', 'p90')):
            r = radii[:, index]
            residual = r - np.polyval(np.polyfit(x - lo, r, 3), x - lo)
            power = abs(np.fft.rfft(residual * np.hanning(len(x)))) ** 2
            frequency = np.fft.rfftfreq(len(x), d=.2)
            eligible = np.where((frequency >= 1 / 3) & (frequency <= 1 / .5))[0]
            peaks = eligible[np.argsort(power[eligible])[-5:][::-1]]
            series.append({'statistic': label, 'radius_mean_mm': float(r.mean()),
                           'detrended_rms_mm': float(np.sqrt(np.mean(residual ** 2))),
                           'candidate_peaks': [{'pitch_mm': float(1 / frequency[i]),
                                                'fraction_of_band_power': float(power[i] / power[eligible].sum())}
                                               for i in peaks]})
        reports.append({'x_interval_mm': [lo, hi], 'sample_step_mm': .2, 'series': series})
    return {'reference_sha256': hashlib.sha256(body).hexdigest(),
            'scope': 'Axial median and percentile radii of the repaired scan, after cubic detrending. Candidate spectral peaks alone do not establish thread pitch.',
            'searched_pitch_range_mm': [.5, 3.0], 'windows': reports,
            'decision': 'Review agreement across both disjoint windows and radial statistics; retain smooth proxy unless a repeatable dominant signal is resolved.'}


if __name__ == '__main__':
    result = measure()
    output = ROOT / 'references/lead-screw-pitch-assessment.json'
    output.write_text(json.dumps(result, indent=2) + '\n')
    for window in result['windows']:
        print(window, flush=True)
