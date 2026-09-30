from pathlib import Path
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
root=Path(__file__).resolve().parents[1]
data=json.loads((root/'build/fold-profiles-audit.json').read_text())
wanted=[('continuous_end',10),('continuous_end',29),('continuous_end',34),('long_side',0),('long_side',-29),('long_side',48),('split_end',24),('split_end',17),('split_end',39)]
fig,axes=plt.subplots(3,3,figsize=(13,11),layout='constrained')
for ax,(name,station) in zip(axes.flat,wanted):
    row=next(r for r in data['sections'] if r['run']==name and r['station_mm']==station)
    for version,color in [('before','#9a9a9a'),('after','#1b6cac')]:
        for i,p in enumerate(row[version]['profiles_radial_z']):
            p=np.asarray(p)
            ax.plot(p[:,0],p[:,1],color=color,label=version if i==0 else None,linewidth=1.3)
    ax.set(title=f'{name.replace("_"," ")} | station {station} mm',xlabel='Outward from fitted rim (mm)',ylabel='Z (mm)',xlim=(-7,1),ylim=(-1,6),aspect='equal')
    ax.grid(alpha=.2)
axes[0,0].legend()
fig.suptitle('Back-cover fold cross-sections: curved bends retained; straight runs and corner blends')
fig.savefig(root/'build/fold-profiles-comparison.png',dpi=150)
