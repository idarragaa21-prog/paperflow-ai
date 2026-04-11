// Demo mode: mock data when backend is unreachable
export const DEMO_MODE = import.meta.env.VITE_DEMO_MODE === 'true';

export const demoUser = { id: 'demo', email: 'demo@paperflow.ai', full_name: 'Demo User' };

export const demoProjects = [
  { id: 'p1', title: 'Distal Radius Fracture Outcomes in Older Adults', clinical_area: 'Orthopedics', archived: false },
  { id: 'p2', title: 'COVID-19 Long-term Pulmonary Sequelae Meta-analysis', clinical_area: 'Pulmonology', archived: false },
  { id: 'p3', title: 'SGLT2 Inhibitors in Heart Failure with Preserved EF', clinical_area: 'Cardiology', archived: false },
  { id: 'p4', title: 'Bariatric Surgery vs GLP-1 in T2DM Remission', clinical_area: 'Endocrinology', archived: false },
];

export const demoCounts: Record<string, any> = {
  p1: { papers: 47, notes: 12, references: 38, meta_studies_current: 8 },
  p2: { papers: 63, notes: 9, references: 55, meta_studies_current: 14 },
  p3: { papers: 29, notes: 7, references: 24, meta_studies_current: 5 },
  p4: { papers: 18, notes: 4, references: 15, meta_studies_current: 3 },
};

export const demoPapers = [
  { id: 'paper1', title: 'Functional outcomes after volar locking plate fixation of distal radius fractures in patients over 65 years', authors: 'Johnson A, Smith B, Williams C', journal: 'J Hand Surg', year: 2023, status: 'ready', source_provider: 'pubmed', is_favorite: false },
  { id: 'paper2', title: 'Conservative vs surgical management of distal radius fractures: systematic review and meta-analysis', authors: 'Chen X, Rodriguez M', journal: 'Bone Joint J', year: 2022, status: 'ready', source_provider: 'pubmed', is_favorite: true },
  { id: 'paper3', title: 'Patient-reported outcomes after distal radius fracture treatment in elderly patients', authors: 'Davis K, Thompson L', journal: 'Clin Orthop', year: 2023, status: 'processing', source_provider: 'manual_upload', is_favorite: false },
  { id: 'paper4', title: 'Radiographic predictors of functional outcomes following distal radius fracture fixation', authors: 'Martinez F et al.', journal: 'J Orthop Trauma', year: 2021, status: 'ready', source_provider: 'pubmed', is_favorite: false },
  { id: 'paper5', title: 'Complication rates after volar plating vs external fixation', authors: 'Lee J, Park S, Kim H', journal: 'Injury', year: 2022, status: 'failed', source_provider: 'pubmed', is_favorite: false },
];
