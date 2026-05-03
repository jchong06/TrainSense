// Official MTA Brand Colors
export const MTA_COLORS: { [route: string]: { background: string; text: string } } = {
  'A': { background: '#0062CF', text: '#FFFFFF' },
  'B': { background: '#EB6800', text: '#FFFFFF' },
  'C': { background: '#0062CF', text: '#FFFFFF' },
  'D': { background: '#EB6800', text: '#FFFFFF' },
  'E': { background: '#0062CF', text: '#FFFFFF' },
  'F': { background: '#EB6800', text: '#FFFFFF' },
  'G': { background: '#79B534', text: '#FFFFFF' },
  'J': { background: '#8E5C33', text: '#FFFFFF' },
  'L': { background: '#7C858C', text: '#FFFFFF' },
  'M': { background: '#EB6800', text: '#FFFFFF' },
  'N': { background: '#F6BC26', text: '#FFFFFF' },
  'Q': { background: '#F6BC26', text: '#FFFFFF' },
  'R': { background: '#F6BC26', text: '#FFFFFF' },
  'S': { background: '#7C858C', text: '#FFFFFF' },
  'T': { background: '#008EB7', text: '#FFFFFF' },
  'W': { background: '#F6BC26', text: '#FFFFFF' },
  'Z': { background: '#8E5C33', text: '#FFFFFF' },
  '1': { background: '#D82233', text: '#FFFFFF' },
  '2': { background: '#D82233', text: '#FFFFFF' },
  '3': { background: '#D82233', text: '#FFFFFF' },
  '4': { background: '#009952', text: '#FFFFFF' },
  '5': { background: '#009952', text: '#FFFFFF' },
  '6': { background: '#009952', text: '#FFFFFF' },
  '7': { background: '#9A38A1', text: '#FFFFFF' },
  '6X': { background: '#009952', text: '#FFFFFF' },
  '7X': { background: '#9A38A1', text: '#FFFFFF' },
  'FX': { background: '#EB6800', text: '#FFFFFF' },
};

export function getMtaColor(routeId: string) {
  return MTA_COLORS[routeId] || { background: '#333333', text: '#FFFFFF' };
} 