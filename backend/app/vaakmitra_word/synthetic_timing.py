"""PHN012: deterministic recording-condition probes, not synthetic disorders."""
import numpy as np
from scipy.signal import stft,istft,resample


def time_stretch(wave,rate):
    y=np.asarray(wave,dtype=np.float32)
    if y.ndim!=1 or len(y)<400 or not np.isfinite(y).all() or not .5<=rate<=2:
        raise ValueError('Finite mono audio and bounded rate required')
    if rate==1:return y.copy()
    nfft=min(512,len(y));hop=nfft//4
    _,_,s=stft(y,fs=16000,nperseg=nfft,noverlap=nfft-hop,boundary='zeros',padded=True)
    positions=np.arange(0,s.shape[1]-1,rate)
    output=np.zeros((s.shape[0],len(positions)),dtype=np.complex64)
    advance=2*np.pi*hop*np.arange(s.shape[0])/nfft
    phase=np.angle(s[:,0]).astype(np.float64)
    for j,pos in enumerate(positions):
        i=int(pos);alpha=pos-i
        magnitude=(1-alpha)*np.abs(s[:,i])+alpha*np.abs(s[:,i+1])
        output[:,j]=magnitude*np.exp(1j*phase)
        delta=np.angle(s[:,i+1])-np.angle(s[:,i])-advance
        delta-=2*np.pi*np.round(delta/(2*np.pi))
        phase+=advance+delta
    _,result=istft(output,fs=16000,nperseg=nfft,noverlap=nfft-hop,boundary=True)
    target=round(len(y)/rate)
    result=np.pad(result,(0,max(0,target-len(result))))[:target].astype(np.float32)
    return result


def pitch_shift(wave,semitones):
    if not -4<=semitones<=4:raise ValueError('Bounded pitch shift required')
    factor=2**(semitones/12)
    expanded=time_stretch(wave,1/factor)
    return resample(expanded,len(wave)).astype(np.float32)


def robustness_variants(wave,seed):
    y=np.asarray(wave,dtype=np.float32)
    if y.ndim!=1 or len(y)<800 or not np.isfinite(y).all():raise ValueError('Finite public source required')
    rng=np.random.default_rng(seed);n=len(y);middle=n//2;a=n*35//100;b=n*70//100
    noise=rng.normal(size=n).astype(np.float32)
    noise*=max(float(np.sqrt(np.mean(y.astype(np.float64)**2))),1e-8)/max(float(np.sqrt(np.mean(noise**2))),1e-8)/10
    tail=y.copy();tail[n*3//4:]*=.1
    variants={
        'clean':y.copy(),
        'uneven_pauses':np.concatenate([y[:a],np.zeros(4000,dtype=np.float32),y[a:b],np.zeros(10400,dtype=np.float32),y[b:]]),
        'long_pause':np.concatenate([y[:middle],np.zeros(12800,dtype=np.float32),y[middle:]]),
        'low_volume':y*.1,
        'high_pitch_plus3st':pitch_shift(y,3),
        'fast_rate1p3':time_stretch(y,1.3),
        'slow_rate0p75':time_stretch(y,.75),
        'uneven_rate':np.concatenate([time_stretch(y[:middle],.8),time_stretch(y[middle:],1.25)]),
        'quiet_ending':tail,
        'noise20db':y+noise,
    }
    for name,data in variants.items():
        if name=='clean':continue
        peak=float(np.max(np.abs(data)))
        if peak>.99:variants[name]=data*(.99/peak)
    return variants
