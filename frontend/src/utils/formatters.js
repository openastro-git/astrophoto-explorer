// Normalize distance values to consistent format
export function normalizeDistance(distance) {
  if (!distance || typeof distance !== 'string') {
    return distance;
  }

  distance = distance.trim();

  // Remove everything in parentheses (like secondary units)
  distance = distance.replace(/\s*\([^)]*\)/g, '').trim();

  // Remove uncertainty values (± notation)
  distance = distance.replace(/\s*±.*?(?=\s|$)/g, '').trim();

  // Extract number and unit parts
  const match = distance.match(/^([\d.,\s]+)(.*)/);
  if (!match) {
    return distance;
  }

  let numberStr = match[1].trim();
  let unit = match[2].trim().toLowerCase();

  // Remove spaces from number string
  numberStr = numberStr.replace(/\s+/g, '');

  // Parse the number, handling comma and period as separators
  let number;
  const lastCommaIndex = numberStr.lastIndexOf(',');
  const lastPeriodIndex = numberStr.lastIndexOf('.');

  if (lastCommaIndex === -1 && lastPeriodIndex === -1) {
    // No separators - straightforward integer
    number = parseInt(numberStr);
  } else {
    // Determine which separator is decimal by checking digits after
    const lastSeparatorIndex = Math.max(lastCommaIndex, lastPeriodIndex);
    const digitsAfter = numberStr.length - lastSeparatorIndex - 1;

    if (digitsAfter > 2) {
      // More than 2 digits after = thousands separator
      numberStr = numberStr.replace(/[,.]/g, '');
      number = parseInt(numberStr);
    } else {
      // Likely decimal point
      const beforeDecimal = numberStr.substring(0, lastSeparatorIndex).replace(/[,.]/g, '');
      const afterDecimal = numberStr.substring(lastSeparatorIndex + 1);
      numberStr = beforeDecimal + '.' + afterDecimal;
      number = parseFloat(numberStr);
    }
  }

  if (isNaN(number)) {
    return distance;
  }

  // Handle unit conversion
  let value = number;
  let finalUnit = 'light-years';

  if (unit.includes('kly')) {
    value = value * 1000;
  } else if (unit.includes('mly')) {
    value = value * 1000000;
    finalUnit = 'million light-years';
    value = value / 1000000; // Convert back to millions
  } else if (unit.includes('million')) {
    finalUnit = 'million light-years';
  }

  // Format output
  if (finalUnit === 'million light-years') {
    // Show with decimal places for millions
    return `${value.toLocaleString('en-US', { maximumFractionDigits: 3, minimumFractionDigits: 0 })} ${finalUnit}`;
  } else {
    // Show as integer for light-years
    return `${Math.round(value).toLocaleString('en-US')} ${finalUnit}`;
  }
}

// Get relative path by removing folder prefix
export function getRelativePath(fullPath, folderPath) {
  if (!folderPath || !fullPath) return fullPath;

  // Normalize paths for comparison (handle both forward and back slashes)
  const normalizedFolder = folderPath.replace(/\\/g, '/').replace(/\/$/, '');
  const normalizedPath = fullPath.replace(/\\/g, '/');

  // Remove the prefix
  let relativePath = normalizedPath;
  if (normalizedPath.startsWith(normalizedFolder)) {
    relativePath = normalizedPath.substring(normalizedFolder.length);
  }

  // Remove file name from the path
  relativePath = relativePath.replace(/\/?[^\/]*$/, '');

  // Remove leading slashes
  relativePath = relativePath.replace(/^[\/\\]+/, '');

  return relativePath || fullPath;
}

// Filter groups by search query
export function filterGroups(groups, searchQuery) {
  if (!searchQuery.trim()) {
    return groups;
  }

  const query = searchQuery.toLowerCase();
  return groups.filter(group => {
    // Check if group name matches
    if (group.object.toLowerCase().includes(query)) {
      return true;
    }

    // Check if any filename in the group matches
    if (group.files && group.files.some(file =>
      file.filename.toLowerCase().includes(query)
    )) {
      return true;
    }

    return false;
  });
}
