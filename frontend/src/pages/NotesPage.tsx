import { useEffect, useRef, useState } from 'react';
import type { NoteRow, NoteDetail } from '../types/api';
import { useParams } from 'react-router-dom';
import { api } from '../services/api';
