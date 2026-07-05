"""
Advanced stretching algorithms for astronomical images.
Implements MTF (Midtone Transfer Function) autostretch similar to PixInsight/Siril.

Siril MTF Formula (from https://free-astro.org/siril_doc-en/):
    xp = (original - shadows) / (highlights - shadows)
    pixel = ((midtones - 1) * xp) / (((2 * midtones - 1) * xp) - midtones)

This implementation uses unlinked channel stretching for color images,
where each RGB channel is stretched independently for better color balance.
"""

import numpy as np
from astropy.visualization import ZScaleInterval
import logging

logger = logging.getLogger(__name__)

def compute_robust_stats(data, use_histogram=True):
    """
    Compute robust statistics using histogram-based approach.
    Only uses pixels below median to avoid bright-tail inflation.
    
    Returns: (median, std_low)
    """
    if use_histogram:
        # Convert to 12-bit for histogram computation
        data_12bit = (np.clip(data, 0, 1) * 4095).astype(np.uint16)
        
        # Build histogram
        hist = np.bincount(data_12bit.ravel(), minlength=4096)
        total = hist.sum()
        
        if total == 0:
            return 0.0, 0.0
        
        # Find median from CDF
        cdf = np.cumsum(hist)
        med_idx = np.searchsorted(cdf, (total + 1) // 2)
        median = med_idx / 4095.0
        
        # Compute std only from pixels <= median (robust against bright outliers)
        bins = np.arange(med_idx + 1, dtype=np.float64) / 4095.0
        hist_low = hist[:med_idx + 1]
        total_low = hist_low.sum()
        
        if total_low > 0:
            mean_low = (hist_low * bins).sum() / total_low
            var_low = (hist_low * (bins - mean_low)**2).sum() / total_low
            std_low = np.sqrt(max(1e-12, var_low))
        else:
            std_low = 0.0
        
        return median, std_low
    else:
        # Fallback to simple median/std
        median = np.median(data)
        std = np.std(data[data <= median])
        return median, std

def mtf_stretch(data, midtone=0.5, shadows_clip=0.0, highlights_clip=1.0):
    """
    Apply Midtone Transfer Function (MTF) stretch.
    
    The MTF formula is: MTF(m, x) = ((m - 1) * x) / ((2m - 1) * x - m)
    where m is the midtone balance parameter (0 < m < 1)
    
    Args:
        data: Input image data (normalized 0-1)
        midtone: Midtone balance (0-1), default 0.5 means no change
        shadows_clip: Shadow clipping point (0-1)
        highlights_clip: Highlight clipping point (0-1)
    
    Returns:
        Stretched image data
    """
    # Clip shadows and highlights, ensuring pixels below BP map to 0
    data_clipped = np.clip(data, shadows_clip, highlights_clip)
    
    # Normalize to 0-1 range after clipping
    if highlights_clip > shadows_clip:
        # Since data_clipped is within [shadows_clip, highlights_clip],
        # data_normalized is guaranteed to be in [0.0, 1.0] without another np.clip
        data_normalized = (data_clipped - shadows_clip) / (highlights_clip - shadows_clip)
    else:
        data_normalized = np.clip(data_clipped, 0.0, 1.0)
    
    # Apply MTF transformation
    if abs(midtone - 0.5) < 1e-6:
        # No transformation needed when midtone is 0.5
        return data_normalized
    
    # MTF formula: ((m - 1) * x) / ((2m - 1) * x - m)
    m = midtone
    numerator = (m - 1) * data_normalized
    denominator = (2 * m - 1) * data_normalized - m
    
    # Since m is clipped to [0.001, 0.999] and data_normalized is in [0, 1],
    # the denominator is always bounded away from zero. We divide directly.
    stretched = numerator / denominator
    
    return np.clip(stretched, 0.0, 1.0)

def auto_stretch_channel(data, target_background=0.17, shadows_clipping=-2.8, qfloor=0.001):
    """
    Automatic stretch for a single channel using histogram-based robust statistics.
    Based on Siril's autostretch algorithm.
    
    Args:
        data: Input channel data (MUST be normalized 0-1)
        target_background: Target median value after stretch (0-1), default 0.17 (17%)
        shadows_clipping: Shadow clipping in sigma units from median (negative), default -2.8
        qfloor: Percentile floor to prevent BP from pegging to 0, default 0.001 (0.1%)
    
    Returns:
        Tuple of (shadows_clip, midtone, highlights_clip) parameters
    """
    # Data should already be normalized to 0-1
    if np.max(data) > 1.0 or np.min(data) < 0.0:
        # Normalize if not already done
        data_min, data_max = np.min(data), np.max(data)
        if data_max > data_min:
            data = (data - data_min) / (data_max - data_min)
        else:
            return 0.0, 0.5, 1.0
    
    # Subsample data for calculating statistics to speed up significantly on large FITS files.
    # Take a grid sample targeting approximately 250,000 pixels.
    num_pixels = data.size
    if num_pixels > 250000:
        step = int(np.sqrt(num_pixels / 250000))
        step = max(1, step)
        stats_data = data[::step, ::step]
    else:
        stats_data = data

    # Compute robust statistics (only using lower half of histogram)
    median, std_low = compute_robust_stats(stats_data)
    
    # Calculate percentile floor (prevents BP from going to absolute 0)
    if qfloor > 0:
        floor_value = np.percentile(stats_data, qfloor * 100)
    else:
        floor_value = 0.0
    
    # Calculate shadow clipping point (black point)
    # shadows_clipping is negative (e.g., -1.25), so we ADD it (which subtracts from median)
    if std_low > 0:
        shadows_clip = max(floor_value, median + shadows_clipping * std_low)
    else:
        shadows_clip = floor_value
    
    shadows_clip = np.clip(shadows_clip, 0.0, 0.99)
    
    # Highlights clipping at 1.0 (no clipping)
    highlights_clip = 1.0
    
    # Calculate midtone to achieve target background
    # From Siril docs: For xp = m, MTF = 0.5
    # This means the midtone parameter m is the input value that maps to 0.5 output
    # 
    # We want the normalized_median to map to target_background
    # But the MTF function always maps m -> 0.5
    # 
    # So we need to find what input value, when passed through MTF with parameter m,
    # gives us target_background as output.
    # 
    # MTF(x, m) = ((m - 1) * x) / ((2m - 1) * x - m) = target
    # Solving for m when x = normalized_median:
    # target * ((2m - 1) * x - m) = (m - 1) * x
    # target * (2m*x - x - m) = m*x - x
    # 2*target*m*x - target*x - target*m = m*x - x
    # 2*target*m*x - target*m - m*x = target*x - x
    # m*(2*target*x - target - x) = x*(target - 1)
    # m = x*(target - 1) / (2*target*x - target - x)
    # m = x*(target - 1) / (x*(2*target - 1) - target)
    
    if median > shadows_clip and median < highlights_clip:
        normalized_median = (median - shadows_clip) / (highlights_clip - shadows_clip)
        
        if normalized_median > 1e-9 and normalized_median < 1.0:
            x = normalized_median
            t = target_background
            
            numerator = x * (t - 1.0)
            denominator = x * (2.0 * t - 1.0) - t
            
            if abs(denominator) > 1e-10:
                midtone = numerator / denominator
                midtone = np.clip(midtone, 0.001, 0.999)
            else:
                midtone = 0.5
        else:
            midtone = 0.5
    else:
        midtone = 0.5
    
    # Log calculated parameters for debugging
    raw_median = np.median(data)
    logger.debug(f"Stretch params - raw_median: {raw_median:.4f}, shadows: {shadows_clip:.4f}, "
                 f"midtone: {midtone:.4f}, highlights: {highlights_clip:.4f}")
    
    return shadows_clip, midtone, highlights_clip

def auto_stretch_unlinked(data, target_background=0.17, shadows_clipping=-2.8):
    """
    Apply automatic stretch with unlinked channels (for color images).
    Each channel is stretched independently for better color balance.
    Based on Siril's autostretch with unlinked channels.
    
    Args:
        data: Input image data, shape (H, W) for grayscale or (H, W, 3) for RGB
        target_background: Target median value after stretch (0-1), default 0.17 (20%)
        shadows_clipping: Shadow clipping in sigma units (negative), default -2.8
    
    Returns:
        Stretched image data (0-1 range)
    """
    if data.ndim == 2:
        # Grayscale image
        # Normalize to 0-1 first
        data_min, data_max = np.min(data), np.max(data)
        if data_max > data_min:
            data_norm = (data - data_min) / (data_max - data_min)
        else:
            return np.zeros_like(data, dtype=np.float32)
        
        shadows, midtone, highlights = auto_stretch_channel(data_norm, target_background, shadows_clipping)
        return mtf_stretch(data_norm, midtone, shadows, highlights)
    
    elif data.ndim == 3 and data.shape[2] == 3:
        # RGB image - process each channel independently (unlinked)
        result = np.zeros_like(data, dtype=np.float32)
        
        for i, color in enumerate(['R', 'G', 'B']):
            channel = data[:, :, i]
            
            # Normalize this channel to 0-1
            ch_min, ch_max = np.min(channel), np.max(channel)
            if ch_max > ch_min:
                channel_norm = (channel - ch_min) / (ch_max - ch_min)
            else:
                channel_norm = np.zeros_like(channel, dtype=np.float32)
            
            # Calculate stretch parameters on normalized data
            shadows, midtone, highlights = auto_stretch_channel(channel_norm, target_background, shadows_clipping)
            logger.debug(f"{color} channel: shadows={shadows:.4f}, midtone={midtone:.4f}, highlights={highlights:.4f}")
            
            # Apply MTF stretch
            result[:, :, i] = mtf_stretch(channel_norm, midtone, shadows, highlights)
        
        return result
    
    else:
        raise ValueError(f"Unsupported data shape: {data.shape}")

def auto_stretch_linked(data, target_background=0.17, shadows_clipping=-2.8):
    """
    Apply automatic stretch with linked channels (same for all RGB channels).
    This is the standard/default approach used by Siril.
    Each channel uses the same stretch parameters based on the overall image statistics.
    
    Args:
        data: Input image data, shape (H, W) for grayscale or (H, W, 3) for RGB
        target_background: Target median value after stretch (0-1), default 0.17 (17%)
        shadows_clipping: Shadow clipping in sigma units (negative), default -2.8
    
    Returns:
        Stretched image data (0-1 range)
    """
    if data.ndim == 2:
        # Grayscale image
        data_min, data_max = np.min(data), np.max(data)
        if data_max > data_min:
            data_norm = (data - data_min) / (data_max - data_min)
        else:
            return np.zeros_like(data, dtype=np.float32)
        
        shadows, midtone, highlights = auto_stretch_channel(data_norm, target_background, shadows_clipping)
        return mtf_stretch(data_norm, midtone, shadows, highlights)
    
    elif data.ndim == 3 and data.shape[2] == 3:
        # RGB image - calculate stretch parameters from luminance/intensity
        # Convert to grayscale using standard luminance weights (ITU-R BT.709)
        R, G, B = data[:, :, 0], data[:, :, 1], data[:, :, 2]
        luminance = 0.2126 * R + 0.7152 * G + 0.0722 * B
        
        # Normalize luminance to 0-1
        lum_min, lum_max = np.min(luminance), np.max(luminance)
        if lum_max > lum_min:
            lum_norm = (luminance - lum_min) / (lum_max - lum_min)
        else:
            return np.zeros_like(data, dtype=np.float32)
        
        # Calculate stretch parameters from luminance
        shadows, midtone, highlights = auto_stretch_channel(lum_norm, target_background, shadows_clipping)
        logger.debug(f"Linked channels: shadows={shadows:.4f}, midtone={midtone:.4f}, highlights={highlights:.4f}")
        
        # Apply the same stretch to each channel
        result = np.zeros_like(data, dtype=np.float32)
        for i, color in enumerate(['R', 'G', 'B']):
            channel = data[:, :, i]
            
            # Normalize this channel to 0-1 (using its own min/max)
            ch_min, ch_max = np.min(channel), np.max(channel)
            if ch_max > ch_min:
                channel_norm = (channel - ch_min) / (ch_max - ch_min)
            else:
                channel_norm = np.zeros_like(channel, dtype=np.float32)
            
            # Apply the stretch parameters from luminance to this channel
            result[:, :, i] = mtf_stretch(channel_norm, midtone, shadows, highlights)
        
        return result
    
    else:
        raise ValueError(f"Unsupported data shape: {data.shape}")

def generate_preview_mtf(data, size=(800, 800), target_background=0.17, shadows_clipping=-2.8, contrast_boost=1.1, linked_channels=True):
    """
    Generate a preview with MTF autostretch at specified size.
    
    Args:
        data: Input FITS data
        size: Target size (width, height)
        target_background: Target background level (0-1), default 0.17 (17%)
        shadows_clipping: Shadow clipping in sigma units (negative), default -2.8
        contrast_boost: Contrast enhancement factor (>1.0 increases contrast), default 1.1
        linked_channels: If True (default), uses same stretch for all RGB channels (Siril standard).
                        If False, stretches each channel independently (better color balance).
    
    Returns:
        8-bit RGB or grayscale image array
    """
    # Apply MTF autostretch with linked or unlinked channels
    if linked_channels:
        stretched = auto_stretch_linked(data, target_background=target_background, shadows_clipping=shadows_clipping)
    else:
        stretched = auto_stretch_unlinked(data, target_background=target_background, shadows_clipping=shadows_clipping)
    
    # Apply contrast boost if specified
    if contrast_boost != 1.0:
        # Apply a simple power curve for contrast enhancement
        # Values > 1.0 increase contrast, < 1.0 decrease contrast
        stretched = np.power(stretched, 1.0 / contrast_boost)
        stretched = np.clip(stretched, 0.0, 1.0)
    
    # Convert to 8-bit
    stretched_8bit = (stretched * 255).clip(0, 255).astype(np.uint8)
    
    # Resize if needed using PIL (much faster than ndimage.zoom)
    if stretched_8bit.shape[0] > size[1] or stretched_8bit.shape[1] > size[0]:
        from PIL import Image
        if stretched_8bit.ndim == 2:
            img = Image.fromarray(stretched_8bit, mode='L')
        else:
            img = Image.fromarray(stretched_8bit, mode='RGB')
            
        # Calculate new size maintaining aspect ratio
        scale = min(size[0] / stretched_8bit.shape[1], size[1] / stretched_8bit.shape[0])
        new_width = int(stretched_8bit.shape[1] * scale)
        new_height = int(stretched_8bit.shape[0] * scale)
        
        img = img.resize((new_width, new_height), Image.Resampling.BILINEAR)
        stretched_8bit = np.array(img)
    
    return stretched_8bit
