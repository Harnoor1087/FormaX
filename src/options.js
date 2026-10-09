// Single source of truth for dashboard controls. Values are what the backend receives.
export const OUTPUT_TYPES = [
  { id: 'advisory', label: 'Advisory' },
  { id: 'linkedin_post', label: 'LinkedIn post' },
  { id: 'twitter_thread', label: 'Twitter/X thread' },
  { id: 'executive_summary', label: 'Executive summary' },
  { id: 'presentation', label: 'Presentation' },
  { id: 'infographic', label: 'Infographic content' },
  { id: 'video_package', label: 'Video package' },
];

export const PARAMS = [
  { key: 'audience', label: 'Audience', options: [
    ['general public', 'General public'], ['government officials', 'Government officials'],
    ['leadership', 'Leadership'], ['field staff', 'Field staff'],
    ['technical experts', 'Technical experts'], ['media', 'Media'] ] },
  { key: 'tone', label: 'Tone', options: [
    ['formal', 'Formal'], ['neutral', 'Neutral'], ['urgent', 'Urgent'],
    ['friendly', 'Friendly'], ['persuasive', 'Persuasive'] ] },
  { key: 'language', label: 'Language', options: [
    ['English', 'English'], ['Hindi', 'Hindi'], ['Punjabi', 'Punjabi'] ] },
  { key: 'detail_level', label: 'Level of detail', options: [
    ['brief', 'Brief'], ['medium', 'Medium'], ['detailed', 'Detailed'] ] },
  { key: 'objective', label: 'Communication objective', options: [
    ['inform', 'Inform'], ['alert', 'Alert'], ['educate', 'Educate'],
    ['persuade', 'Persuade'], ['summarise', 'Summarise'] ] },
];

export const DEFAULTS = {
  audience: 'government officials', tone: 'formal', language: 'English',
  detail_level: 'medium', objective: 'inform',
};
