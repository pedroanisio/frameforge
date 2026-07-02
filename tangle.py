# NON-RUNNABLE RESEARCH SCRATCH — do not import or execute.
# Hardcoded foreign paths (/mnt/user-data/uploads, /home/claude) and dependencies
# (skimage, matplotlib) that are not in this repo's dependency groups.
# Assessment: its finding — mollified level-set regions are (sigma, level)
# parameter-sensitive, hence the ensemble — is preserved as the consensus method in
# framegraph/vision/infrastructure/regions.py (see consensus_smooth_regions).
import cv2, numpy as np
from skimage import measure

im=cv2.imread('/mnt/user-data/uploads/images__2_.jpeg',cv2.IMREAD_GRAYSCALE)
t,bw=cv2.threshold(im,0,255,cv2.THRESH_BINARY_INV+cv2.THRESH_OTSU)
H,W=bw.shape
free=(bw==0).astype(np.uint8); ff=free.copy(); m=np.zeros((H+2,W+2),np.uint8)
cv2.floodFill(ff,m,(0,0),2); enclosed=(ff==1).astype(np.uint8)*255
n,lab,stats,_=cv2.connectedComponentsWithStats(enclosed,8)
areas=stats[1:,4]; order=np.argsort(-areas)+1

def ext(mask):
    cs,_=cv2.findContours(mask.astype(np.uint8),cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_NONE)
    return max(cs,key=cv2.contourArea).reshape(-1,2).astype(float)
def resample(P,M=2048):
    P=np.vstack([P,P[0]]); seg=np.sqrt((np.diff(P,axis=0)**2).sum(1))
    s=np.concatenate([[0],np.cumsum(seg)]); u=np.linspace(0,s[-1],M,endpoint=False)
    return np.interp(u,s,P[:,0]),np.interp(u,s,P[:,1])
def smooth(P,N,M=2048):
    x,y=resample(P,M); z=x+1j*y; Z=np.fft.fft(z)/M; k=np.fft.fftfreq(M,1.0/M)
    keep=np.abs(k)<=N; Zt=np.where(keep,Z,0); zr=np.fft.ifft(Zt*M)
    xr,yr=zr.real,zr.imag; A=0.5*np.abs(np.sum(xr*np.roll(yr,-1)-np.roll(xr,-1)*yr))
    return xr,yr,A

print("=== genuine enclosed cells: does area-derivation still hold? ===")
for rank in [0,2,6]:
    cid=order[rank]; mask=(lab==cid); P=ext(mask); pix=int(mask.sum())
    x,y,w,h,_=stats[cid]
    _,_,A=smooth(P,32)
    print(f"cell rank{rank}: pixel_area={pix:6d} bbox=({x},{y},{w},{h}) smoothed_area(N=32)={A:8.1f} relerr={abs(A-pix)/pix*100:5.2f}%")

print("\n=== FACE has no intrinsic region: mollified ink-density level sets ===")
ink=(bw>0).astype(np.float32)
def density_region_area(sigma, level):
    f=cv2.GaussianBlur(ink,(0,0),sigma); f/=f.max()
    cs=measure.find_contours(f, level)
    # total signed area enclosed by all level-set loops
    tot=0.0
    for c in cs:
        y,x=c[:,0],c[:,1]
        tot+=abs(0.5*np.sum(x*np.roll(y,-1)-np.roll(x,-1)*y))
    return f, tot, len(cs)
print("fixed level=0.30, vary sigma:")
for s in [2,4,8,12,20]:
    _,A,nc=density_region_area(s,0.30); print(f"  sigma={s:3d}: enclosed_area={A:8.0f}px  loops={nc}")
print("fixed sigma=8, vary level:")
for L in [0.15,0.30,0.50,0.70]:
    _,A,nc=density_region_area(8,L); print(f"  level={L:.2f}: enclosed_area={A:8.0f}px  loops={nc}")

import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
rgb=cv2.cvtColor(cv2.imread('/mnt/user-data/uploads/images__2_.jpeg'),cv2.COLOR_BGR2RGB)
fig,ax=plt.subplots(2,2,figsize=(12,13)); fig.patch.set_facecolor('white')

ax[0,0].imshow(rgb); ax[0,0].set_title('Fixture: tangled open linework',fontsize=11); ax[0,0].axis('off')

# B: largest CC silhouette
nC,labC,statsC,_=cv2.connectedComponentsWithStats(bw,8)
big=1+int(np.argmax(statsC[1:,4])); Pbig=ext(labC==big)
ax[0,1].imshow(rgb,alpha=0.35)
ax[0,1].plot(np.append(Pbig[:,0],Pbig[0,0]),np.append(Pbig[:,1],Pbig[0,1]),'-',color='#d62728',lw=1.4)
ax[0,1].set_title('Largest connected component = 95.4% of ink\n→ "the region" is the whole-drawing silhouette',fontsize=10); ax[0,1].axis('off')

# C: enclosed cells, genuine ones + smoothed boundaries
disp=np.zeros((H,W,3),np.uint8)+255
rng=np.random.default_rng(0)
for cid in range(1,nC if False else n):
    pass
col=(lab>0)
# color cells by size: tiny=light grey, big=colored
sizemap=np.zeros((H,W),np.float32)
for i in range(1,n): sizemap[lab==i]=stats[i,4]
ax[1,0].imshow(rgb,alpha=0.25)
ax[1,0].imshow(np.ma.masked_where(sizemap<300,np.log10(sizemap+1)),cmap='viridis',alpha=0.7)
for rank,c in [(0,'#d62728'),(2,'#ff7f0e'),(6,'#1f77b4')]:
    P=ext(lab==order[rank]); xr,yr,_=smooth(P,32)
    ax[1,0].plot(np.append(xr,xr[0]),np.append(yr,yr[0]),c,lw=1.8)
ax[1,0].set_title('773 enclosed cells — 84% are <20px noise.\nColored: cells>300px; lines: C∞ boundaries of 3 real cells',fontsize=10); ax[1,0].axis('off')

# D: mollified density level sets, kernel dependence
ax[1,1].imshow(rgb,alpha=0.30)
cols={4:'#1f77b4',8:'#2ca02c',20:'#d62728'}
for s,c in cols.items():
    f=cv2.GaussianBlur(ink,(0,0),s); f/=f.max()
    for cc in measure.find_contours(f,0.30):
        ax[1,1].plot(cc[:,1],cc[:,0],c,lw=1.3)
    # legend proxy
ax[1,1].plot([],[],'#1f77b4',label='σ=4  (98.6k px, 75 loops)')
ax[1,1].plot([],[],'#2ca02c',label='σ=8  (104.8k px, 17 loops)')
ax[1,1].plot([],[],'#d62728',label='σ=20 (177.3k px, 5 loops)')
ax[1,1].legend(fontsize=8,loc='lower right')
ax[1,1].set_title('Mollified density level sets (level=0.30 fixed)\n→ region area & topology depend on blur σ',fontsize=10); ax[1,1].axis('off')
plt.tight_layout(); plt.savefig('/home/claude/tangle_fig.png',dpi=110,bbox_inches='tight'); print('saved')