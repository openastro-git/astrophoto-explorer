// Bright stars for rendering (simplified dataset)
export const constellationStars = [
  // Ursa Major (Big Dipper)
  { name: "Dubhe", ra: 165.93, dec: 61.75, mag: 1.79, spectralType: "K0" },
  { name: "Merak", ra: 165.46, dec: 56.38, mag: 2.37, spectralType: "A1" },
  { name: "Phecda", ra: 178.46, dec: 53.69, mag: 2.44, spectralType: "A0" },
  { name: "Megrez", ra: 183.86, dec: 57.03, mag: 3.31, spectralType: "A3" },
  { name: "Alioth", ra: 193.51, dec: 55.96, mag: 1.77, spectralType: "A0" },
  { name: "Mizar", ra: 200.98, dec: 54.93, mag: 2.27, spectralType: "A2" },
  { name: "Alkaid", ra: 206.89, dec: 49.31, mag: 1.86, spectralType: "B3" },
  
  // Orion
  { name: "Betelgeuse", ra: 88.79, dec: 7.41, mag: 0.50, spectralType: "M2" },
  { name: "Rigel", ra: 78.63, dec: -8.20, mag: 0.13, spectralType: "B8" },
  { name: "Bellatrix", ra: 81.28, dec: 6.35, mag: 1.64, spectralType: "B2" },
  { name: "Alnilam", ra: 84.05, dec: -1.20, mag: 1.69, spectralType: "B0" },
  { name: "Alnitak", ra: 85.19, dec: -1.94, mag: 1.77, spectralType: "O9" },
  { name: "Mintaka", ra: 83.00, dec: -0.30, mag: 2.23, spectralType: "O9" },
  { name: "Saiph", ra: 86.94, dec: -9.67, mag: 2.06, spectralType: "B0" },
  
  // Summer Triangle
  { name: "Vega", ra: 279.23, dec: 38.78, mag: 0.03, spectralType: "A0" },
  { name: "Deneb", ra: 310.36, dec: 45.28, mag: 1.25, spectralType: "A2" },
  { name: "Altair", ra: 297.70, dec: 8.87, mag: 0.77, spectralType: "A7" },
  
  // Cassiopeia
  { name: "Schedar", ra: 10.13, dec: 56.54, mag: 2.23, spectralType: "K0" },
  { name: "Caph", ra: 2.29, dec: 59.15, mag: 2.27, spectralType: "F2" },
  { name: "Gamma Cas", ra: 14.18, dec: 60.72, mag: 2.47, spectralType: "B0" },
  { name: "Ruchbah", ra: 21.45, dec: 60.24, mag: 2.68, spectralType: "A5" },
  { name: "Segin", ra: 25.65, dec: 63.67, mag: 3.38, spectralType: "B3" },
  
  // Other bright stars
  { name: "Polaris", ra: 37.95, dec: 89.26, mag: 1.98, spectralType: "F7" },
  { name: "Arcturus", ra: 213.92, dec: 19.18, mag: -0.05, spectralType: "K2" },
  { name: "Spica", ra: 201.30, dec: -11.16, mag: 0.97, spectralType: "B1" },
  { name: "Antares", ra: 247.35, dec: -26.43, mag: 0.96, spectralType: "M1" },
  { name: "Capella", ra: 79.17, dec: 45.99, mag: 0.08, spectralType: "G8" },
  { name: "Aldebaran", ra: 68.98, dec: 16.51, mag: 0.85, spectralType: "K5" },
  { name: "Regulus", ra: 152.09, dec: 11.97, mag: 1.35, spectralType: "B7" },
  { name: "Sirius", ra: 101.29, dec: -16.72, mag: -1.46, spectralType: "A1" },
  { name: "Procyon", ra: 114.83, dec: 5.23, mag: 0.34, spectralType: "F5" },
  { name: "Castor", ra: 113.65, dec: 31.89, mag: 1.93, spectralType: "A1" },
  { name: "Pollux", ra: 116.33, dec: 28.03, mag: 1.14, spectralType: "K0" },
];

export function spectralTypeToColor(spectralType) {
  const type = spectralType.charAt(0).toUpperCase();
  const colors = {
    O: "#9bb0ff",  // Blue
    B: "#aabfff",  // Blue-white
    A: "#cad7ff",  // White
    F: "#f8f7ff",  // Yellow-white
    G: "#fff4ea",  // Yellow
    K: "#ffd2a1",  // Orange
    M: "#ffcc6f"   // Red
  };
  return colors[type] || "#ffffff";
}

export function magnitudeToSize(mag) {
  const minMag = -1.5;
  const maxMag = 6;
  const minSize = 1;
  const maxSize = 5;
  const clampedMag = Math.max(minMag, Math.min(maxMag, mag));
  const size = maxSize - ((clampedMag - minMag) / (maxMag - minMag)) * (maxSize - minSize);
  return size;
}
