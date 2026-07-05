"""Astrometry data extraction from FITS headers."""
import re


def extract_astrometry_data(hdr):
    """Extract astrometry/WCS data from FITS header for skymap plotting."""
    astrometry = {}
    
    # RA/Dec coordinates (multiple possible keys)
    if 'RA' in hdr:
        astrometry['ra'] = float(hdr['RA'])
    elif 'OBJCTRA' in hdr:
        # Parse RA from format like "02 37 11.000" (HH MM SS)
        ra_str = str(hdr['OBJCTRA'])
        try:
            parts = ra_str.split()
            if len(parts) == 3:
                hours, minutes, seconds = map(float, parts)
                astrometry['ra'] = (hours + minutes/60 + seconds/3600) * 15  # Convert to degrees
        except:
            pass
    elif 'CRVAL1' in hdr:
        astrometry['ra'] = float(hdr['CRVAL1'])
    
    if 'DEC' in hdr:
        astrometry['dec'] = float(hdr['DEC'])
    elif 'OBJCTDEC' in hdr:
        # Parse Dec from format like "+61 28 34.000" (DD MM SS)
        dec_str = str(hdr['OBJCTDEC'])
        try:
            sign = 1 if dec_str[0] != '-' else -1
            dec_str = dec_str.lstrip('+-')
            parts = dec_str.split()
            if len(parts) == 3:
                degrees, minutes, seconds = map(float, parts)
                astrometry['dec'] = sign * (degrees + minutes/60 + seconds/3600)
        except:
            pass
    elif 'CRVAL2' in hdr:
        astrometry['dec'] = float(hdr['CRVAL2'])
    
    # Image dimensions
    if 'NAXIS1' in hdr:
        astrometry['width'] = int(hdr['NAXIS1'])
    if 'NAXIS2' in hdr:
        astrometry['height'] = int(hdr['NAXIS2'])
    
    # Pixel scale (arcsec/pixel)
    if 'XPIXSZ' in hdr and 'FOCALLEN' in hdr:
        pixel_size = float(hdr['XPIXSZ'])  # microns
        focal_length = float(hdr['FOCALLEN'])  # mm
        if focal_length > 0:
            astrometry['pixel_scale'] = (pixel_size / focal_length) * 206.265  # arcsec/pixel
    elif 'CDELT1' in hdr:
        astrometry['pixel_scale'] = abs(float(hdr['CDELT1'])) * 3600  # deg to arcsec
    elif 'CD1_1' in hdr:
        astrometry['pixel_scale'] = abs(float(hdr['CD1_1'])) * 3600  # deg to arcsec
    
    # Field of view (arcminutes)
    if 'pixel_scale' in astrometry and 'width' in astrometry and 'height' in astrometry:
        astrometry['fov_width'] = (astrometry['width'] * astrometry['pixel_scale']) / 60  # arcmin
        astrometry['fov_height'] = (astrometry['height'] * astrometry['pixel_scale']) / 60  # arcmin
    
    # Rotation angle
    if 'CROTA2' in hdr:
        astrometry['rotation'] = float(hdr['CROTA2'])
    elif 'CROTA1' in hdr:
        astrometry['rotation'] = float(hdr['CROTA1'])
    
    # WCS reference pixel
    if 'CRPIX1' in hdr:
        astrometry['crpix1'] = float(hdr['CRPIX1'])
    if 'CRPIX2' in hdr:
        astrometry['crpix2'] = float(hdr['CRPIX2'])
    
    # Coordinate system
    if 'CTYPE1' in hdr:
        astrometry['ctype1'] = str(hdr['CTYPE1'])
    if 'CTYPE2' in hdr:
        astrometry['ctype2'] = str(hdr['CTYPE2'])
    
    # Equinox
    if 'EQUINOX' in hdr:
        astrometry['equinox'] = float(hdr['EQUINOX'])
    
    # Site location (for altitude/azimuth calculations)
    if 'SITELAT' in hdr:
        astrometry['site_lat'] = float(hdr['SITELAT'])
    elif 'OBSLAT' in hdr:
        astrometry['site_lat'] = float(hdr['OBSLAT'])
    
    if 'SITELONG' in hdr:
        astrometry['site_long'] = float(hdr['SITELONG'])
    elif 'OBSLONG' in hdr:
        astrometry['site_long'] = float(hdr['OBSLONG'])
    
    # Altitude and Azimuth at time of observation
    if 'OBJCTALT' in hdr:
        astrometry['altitude'] = float(hdr['OBJCTALT'])
    elif 'CENTALT' in hdr:
        astrometry['altitude'] = float(hdr['CENTALT'])
    
    if 'OBJCTAZ' in hdr:
        astrometry['azimuth'] = float(hdr['OBJCTAZ'])
    elif 'CENTAZ' in hdr:
        astrometry['azimuth'] = float(hdr['CENTAZ'])
    
    # Airmass
    if 'AIRMASS' in hdr:
        astrometry['airmass'] = float(hdr['AIRMASS'])
    
    # Plate solve status
    if 'PLTSOLVD' in hdr:
        astrometry['plate_solved'] = True
    
    return astrometry if astrometry else None


def parse_fits_header_from_string(header_str):
    """Parse FITS header data from a string (e.g., from TIFF description)."""
    astrometry = {}
    
    try:
        # Extract RA
        ra_match = re.search(r"RA\s*=\s*([\d.]+)", header_str)
        if ra_match:
            astrometry['ra'] = float(ra_match.group(1))
        else:
            # Try OBJCTRA format
            objctra_match = re.search(r"OBJCTRA\s*=\s*'([^']+)'", header_str)
            if objctra_match:
                ra_str = objctra_match.group(1).strip()
                parts = ra_str.split()
                if len(parts) == 3:
                    hours, minutes, seconds = map(float, parts)
                    astrometry['ra'] = (hours + minutes/60 + seconds/3600) * 15
        
        # Try CRVAL1 as fallback
        if 'ra' not in astrometry:
            crval1_match = re.search(r"CRVAL1\s*=\s*([\d.]+)", header_str)
            if crval1_match:
                astrometry['ra'] = float(crval1_match.group(1))
        
        # Extract DEC
        dec_match = re.search(r"DEC\s*=\s*([\d.+-]+)", header_str)
        if dec_match:
            astrometry['dec'] = float(dec_match.group(1))
        else:
            # Try OBJCTDEC format
            objctdec_match = re.search(r"OBJCTDEC\s*=\s*'([^']+)'", header_str)
            if objctdec_match:
                dec_str = objctdec_match.group(1).strip()
                sign = 1 if dec_str[0] != '-' else -1
                dec_str = dec_str.lstrip('+-')
                parts = dec_str.split()
                if len(parts) == 3:
                    degrees, minutes, seconds = map(float, parts)
                    astrometry['dec'] = sign * (degrees + minutes/60 + seconds/3600)
        
        # Try CRVAL2 as fallback
        if 'dec' not in astrometry:
            crval2_match = re.search(r"CRVAL2\s*=\s*([\d.+-]+)", header_str)
            if crval2_match:
                astrometry['dec'] = float(crval2_match.group(1))
        
        # Extract image dimensions
        naxis1_match = re.search(r"NAXIS1\s*=\s*(\d+)", header_str)
        if naxis1_match:
            astrometry['width'] = int(naxis1_match.group(1))
        
        naxis2_match = re.search(r"NAXIS2\s*=\s*(\d+)", header_str)
        if naxis2_match:
            astrometry['height'] = int(naxis2_match.group(1))
        
        # Extract pixel scale
        xpixsz_match = re.search(r"XPIXSZ\s*=\s*([\d.]+)", header_str)
        focallen_match = re.search(r"FOCALLEN\s*=\s*([\d.]+)", header_str)
        if xpixsz_match and focallen_match:
            pixel_size = float(xpixsz_match.group(1))
            focal_length = float(focallen_match.group(1))
            if focal_length > 0:
                astrometry['pixel_scale'] = (pixel_size / focal_length) * 206.265
        else:
            cdelt1_match = re.search(r"CDELT1\s*=\s*([\d.E+-]+)", header_str)
            if cdelt1_match:
                astrometry['pixel_scale'] = abs(float(cdelt1_match.group(1))) * 3600
        
        # Calculate FOV if we have the data
        if 'pixel_scale' in astrometry and 'width' in astrometry and 'height' in astrometry:
            astrometry['fov_width'] = (astrometry['width'] * astrometry['pixel_scale']) / 60
            astrometry['fov_height'] = (astrometry['height'] * astrometry['pixel_scale']) / 60
        
        # Extract rotation
        crota2_match = re.search(r"CROTA2\s*=\s*([\d.+-]+)", header_str)
        if crota2_match:
            astrometry['rotation'] = float(crota2_match.group(1))
        
        # Extract site location
        sitelat_match = re.search(r"SITELAT\s*=\s*([\d.+-]+)", header_str)
        if sitelat_match:
            astrometry['site_lat'] = float(sitelat_match.group(1))
        
        sitelong_match = re.search(r"SITELONG\s*=\s*([\d.+-]+)", header_str)
        if sitelong_match:
            astrometry['site_long'] = float(sitelong_match.group(1))
        
        # Extract altitude/azimuth
        objctalt_match = re.search(r"OBJCTALT\s*=\s*([\d.+-]+)", header_str)
        if objctalt_match:
            astrometry['altitude'] = float(objctalt_match.group(1))
        
        objctaz_match = re.search(r"OBJCTAZ\s*=\s*([\d.+-]+)", header_str)
        if objctaz_match:
            astrometry['azimuth'] = float(objctaz_match.group(1))
        
        # Check for plate solve
        if 'PLTSOLVD' in header_str:
            astrometry['plate_solved'] = True
        
    except Exception as e:
        print(f"Error parsing FITS header from string: {e}")
    
    return astrometry if astrometry else None
