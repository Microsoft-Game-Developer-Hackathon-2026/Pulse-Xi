export type GraphicsQuality = 'low' | 'standard' | 'high'
export type CameraPreset = 'broadcast' | 'tactical' | 'isometric' | 'focus' | 'free'

// `standard` is the existing persisted/test contract for the Medium profile.
export const graphicsProfiles = {
  low: { label: 'Low · Performance', dpr: 1, shadows: false, shadowSize: 512, stadium: false, exposure: 1.1 },
  standard: { label: 'Medium · Balanced', dpr: 1.25, shadows: false, shadowSize: 512, stadium: true, exposure: 1.1 },
  high: { label: 'High · Cinematic', dpr: 1.5, shadows: true, shadowSize: 1024, stadium: true, exposure: 1.15 },
} as const

// A 105×68 reference pitch is mapped into the unchanged 100×64 display frame.
// These constants describe original scenery, never measured event distances.
export const referencePitch = { length: 105, width: 68, displayLength: 100, displayWidth: 64 } as const
