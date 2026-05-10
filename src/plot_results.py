# src/plot_results.py
import json, matplotlib.pyplot as plt

MARKERS = {'ibm_v3':'*', 'ibm_v4':'x', 'all_2q':'^', 'max_4q':'o',
           'eff5freq':'s', 'ours':'D'}
COLORS  = {'ibm_v3':'k','ibm_v4':'k','all_2q':'k','max_4q':'k',
           'eff5freq':'g','ours':'r'}

def plot(results_json='results.json'):
    R = json.load(open(results_json))
    n = len(R); cols = 4; rows = (n+cols-1)//cols
    fig, axes = plt.subplots(rows, cols, figsize=(16, 3.2*rows))
    for ax, (name, data) in zip(axes.flat, R.items()):
        for arch, (gates, y) in data.items():
            ax.scatter(gates, y, marker=MARKERS[arch], c=COLORS[arch],
                       s=80, label=arch)
        ax.set_title(name); ax.set_xlabel('post-map gates'); ax.set_ylabel('yield')
    axes.flat[0].legend(loc='best', fontsize=7)
    plt.tight_layout(); plt.savefig('fig12_replication.png', dpi=150)
