export type Locale = 'en' | 'es' | 'hi'
export type Persona = 'casual' | 'analyst' | 'favorite_team' | 'favorite_player' | 'broadcaster'
export type FanPreferences = {
  version: 1
  locale: Locale
  persona: Persona
  favoriteTeamId: string
  favoritePlayerId: string
}

const preferenceKey = 'pulse-xi-fandna-preferences-v1'
const defaultPreferences: FanPreferences = {
  version: 1,
  locale: 'en',
  persona: 'casual',
  favoriteTeamId: '',
  favoritePlayerId: '',
}

const en = {
  workspace: 'Workspace', match_intelligence: 'Match intelligence', sandbox_lab: 'Sandbox Lab', match_data_hub: 'Match Data Hub',
  command_center: 'Command Center', live_match: 'Live match intelligence', select_match: 'Select match',
  home: 'Home', away: 'Away', replay_in_progress: 'Replay in progress', ready_to_replay: 'Ready to replay', end_of_replay: 'End of replay',
  time_machine: 'Time machine', sim_clock: 'Simulation clock · 30 match seconds / real second at 1×',
  seek_match: 'Seek match time', restart: 'Restart', previous_event: 'Previous event', play: 'Play', pause: 'Pause', next_event: 'Next event', speed: 'Speed',
  critical_moments: 'Critical moments', select_to_seek: 'Select to seek', no_goals: 'No goal events at this replay time.',
  match_signals: 'Match signals', computed_from: 'Computed from {count} events', shots: 'Shots', completed_passes: 'Completed passes',
  pass_accuracy: 'Pass accuracy', final_third_entries: 'Final-third entries', recoveries: 'Recoveries', pressure_events: 'Pressure events',
  event_wire: 'Event wire', sequenced_feed: 'Sequenced feed', empty_feed: 'Press play or seek to inspect the event stream.',
  verified_moments: 'ProofTrail / verified moments', rule_based_citations: 'Rule-based · event citations', view_proof: 'View proof · {count} events',
  no_insights: 'Verified insights will appear as the replay reaches them.', fandna_recap: 'FanDNA / recap', loading: 'Loading event-verified recap…',
  view: 'View', language: 'Language', casual: 'Casual fan', analyst: 'Tactical analyst', favorite_team: 'Favorite team',
  favorite_player: 'Favorite player', broadcaster: 'Broadcast producer', follow_team: 'Follow team', follow_player: 'Follow player',
  source_events: 'Source events', fallback: 'English fallback active', locale_status: 'All FanDNA interface labels are translated for this language.',
  recap_error: 'Recap unavailable. Your replay and other analysis remain available.',
  recap_scope: 'Verified goal recap · synthetic events',
}
const es: typeof en = {
  workspace: 'Espacio de trabajo', match_intelligence: 'Análisis del partido', sandbox_lab: 'Laboratorio Sandbox', match_data_hub: 'Centro de datos',
  command_center: 'Centro de control', live_match: 'Análisis del partido en directo', select_match: 'Elegir partido',
  home: 'Local', away: 'Visitante', replay_in_progress: 'Repetición en curso', ready_to_replay: 'Listo para repetir', end_of_replay: 'Fin de la repetición',
  time_machine: 'Línea de tiempo', sim_clock: 'Reloj simulado · 30 segundos de partido por segundo real a 1×',
  seek_match: 'Buscar momento del partido', restart: 'Reiniciar', previous_event: 'Evento anterior', play: 'Reproducir', pause: 'Pausar', next_event: 'Evento siguiente', speed: 'Velocidad',
  critical_moments: 'Momentos clave', select_to_seek: 'Selecciona para ir al momento', no_goals: 'No hay goles en este momento de la repetición.',
  match_signals: 'Indicadores del partido', computed_from: 'Calculado a partir de {count} eventos', shots: 'Tiros', completed_passes: 'Pases completados',
  pass_accuracy: 'Precisión de pase', final_third_entries: 'Entradas al último tercio', recoveries: 'Recuperaciones', pressure_events: 'Eventos de presión',
  event_wire: 'Flujo de eventos', sequenced_feed: 'Flujo secuenciado', empty_feed: 'Reproduce o busca un momento para revisar los eventos.',
  verified_moments: 'ProofTrail / momentos verificados', rule_based_citations: 'Basado en reglas · citas de eventos', view_proof: 'Ver evidencia · {count} eventos',
  no_insights: 'Los datos verificados aparecerán al avanzar la repetición.', fandna_recap: 'FanDNA / resumen', loading: 'Cargando resumen verificado por eventos…',
  view: 'Vista', language: 'Idioma', casual: 'Aficionado', analyst: 'Analista táctico', favorite_team: 'Equipo favorito',
  favorite_player: 'Jugador favorito', broadcaster: 'Productor de transmisión', follow_team: 'Seguir equipo', follow_player: 'Seguir jugador',
  source_events: 'Eventos de origen', fallback: 'Se muestra la versión en inglés', locale_status: 'Todas las etiquetas de FanDNA están traducidas a este idioma.',
  recap_error: 'Resumen no disponible. La repetición y los demás análisis siguen disponibles.',
  recap_scope: 'Resumen verificado de goles · eventos sintéticos',
}
const hi: typeof en = {
  workspace: 'कार्यस्थान', match_intelligence: 'मैच विश्लेषण', sandbox_lab: 'सैंडबॉक्स लैब', match_data_hub: 'मैच डेटा केंद्र',
  command_center: 'कमांड केंद्र', live_match: 'लाइव मैच विश्लेषण', select_match: 'मैच चुनें',
  home: 'घरेलू', away: 'मेहमान', replay_in_progress: 'रीप्ले चल रहा है', ready_to_replay: 'रीप्ले तैयार है', end_of_replay: 'रीप्ले समाप्त',
  time_machine: 'समयरेखा', sim_clock: 'सिमुलेशन घड़ी · 1× पर एक वास्तविक सेकंड में 30 मैच सेकंड',
  seek_match: 'मैच का समय चुनें', restart: 'फिर शुरू करें', previous_event: 'पिछली घटना', play: 'चलाएँ', pause: 'रोकें', next_event: 'अगली घटना', speed: 'गति',
  critical_moments: 'महत्वपूर्ण क्षण', select_to_seek: 'समय पर जाने के लिए चुनें', no_goals: 'इस रीप्ले समय पर कोई गोल नहीं है।',
  match_signals: 'मैच संकेत', computed_from: '{count} घटनाओं से गणना', shots: 'शॉट', completed_passes: 'सफल पास',
  pass_accuracy: 'पास सटीकता', final_third_entries: 'अंतिम तिहाई में प्रवेश', recoveries: 'गेंद वापसी', pressure_events: 'दबाव घटनाएँ',
  event_wire: 'घटना प्रवाह', sequenced_feed: 'क्रमबद्ध फ़ीड', empty_feed: 'घटनाएँ देखने के लिए चलाएँ या समय चुनें।',
  verified_moments: 'ProofTrail / सत्यापित क्षण', rule_based_citations: 'नियम आधारित · घटना संदर्भ', view_proof: 'प्रमाण देखें · {count} घटनाएँ',
  no_insights: 'रीप्ले आगे बढ़ने पर सत्यापित जानकारी दिखाई देगी।', fandna_recap: 'FanDNA / सारांश', loading: 'घटना-सत्यापित सारांश लोड हो रहा है…',
  view: 'दृश्य', language: 'भाषा', casual: 'फुटबॉल प्रशंसक', analyst: 'रणनीति विश्लेषक', favorite_team: 'पसंदीदा टीम',
  favorite_player: 'पसंदीदा खिलाड़ी', broadcaster: 'प्रसारण निर्माता', follow_team: 'टीम का अनुसरण करें', follow_player: 'खिलाड़ी का अनुसरण करें',
  source_events: 'स्रोत घटनाएँ', fallback: 'अंग्रेज़ी विकल्प दिखाया जा रहा है', locale_status: 'FanDNA के सभी इंटरफ़ेस लेबल इस भाषा में हैं।',
  recap_error: 'सारांश उपलब्ध नहीं है। रीप्ले और अन्य विश्लेषण उपलब्ध हैं।',
  recap_scope: 'सत्यापित गोल सारांश · कृत्रिम घटनाएँ',
}
const catalogs: Record<Locale, typeof en> = { en, es, hi }
export type MessageKey = keyof typeof en

export function translate(locale: Locale, key: MessageKey, values: Record<string, string | number> = {}): string {
  const template = catalogs[locale]?.[key] ?? en[key]
  return template.replace(/\{(\w+)\}/g, (_, name: string) => String(values[name] ?? ''))
}

export function hasLocaleFallback(locale: Locale): boolean {
  return (Object.keys(en) as MessageKey[]).some(key => !catalogs[locale]?.[key])
}

const locales = new Set<unknown>(['en', 'es', 'hi'])
const personas = new Set<unknown>(['casual', 'analyst', 'favorite_team', 'favorite_player', 'broadcaster'])
const validId = (value: unknown): value is string => typeof value === 'string' && value.length <= 160 && !/[\x00-\x1f]/.test(value)

export function readFanPreferences(): FanPreferences {
  try {
    const raw = localStorage.getItem(preferenceKey)
    if (!raw || raw.length > 2048) return { ...defaultPreferences }
    const value = JSON.parse(raw)
    if (value?.version !== 1 || !locales.has(value.locale) || !personas.has(value.persona) ||
        !validId(value.favoriteTeamId) || !validId(value.favoritePlayerId)) return { ...defaultPreferences }
    return value as FanPreferences
  } catch {
    return { ...defaultPreferences }
  }
}

export function writeFanPreferences(value: FanPreferences): boolean {
  try {
    localStorage.setItem(preferenceKey, JSON.stringify(value))
    return true
  } catch {
    return false
  }
}
