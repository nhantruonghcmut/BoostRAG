import { apiClient } from './client';
import type {
  DocumentListResponse,
  DocumentRead,
  ReindexDocumentResponse,
  UpdateDocumentAclRequest,
  UploadDocumentResponse,
} from '@/lib/types/api';

export interface UploadDocumentParams {
  file: File;
  requiredLevel: number;
  allowedGroups: string[];
}

export const documentsApi = {
  uploadDocument,
  listDocuments,
  getDocument,
  updateDocumentAcl,
  deleteDocument,
  reindexDocument,
};

export async function uploadDocument({
  file,
  requiredLevel,
  allowedGroups,
}: UploadDocumentParams): Promise<UploadDocumentResponse> {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('required_level', String(requiredLevel));
  formData.append('allowed_groups', JSON.stringify(allowedGroups));

  const response = await apiClient.raw.post<UploadDocumentResponse>(
    '/admin/documents',
    formData,
    {
      transformRequest: [
        (data, headers) => {
          if (headers) {
            delete headers['Content-Type'];
          }
          return data;
        },
      ],
    },
  );
  return response.data;
}

export function listDocuments(params?: { skip?: number; limit?: number }) {
  return apiClient.get<DocumentListResponse>('/admin/documents', { params });
}

export function getDocument(id: string) {
  return apiClient.get<DocumentRead>(`/admin/documents/${id}`);
}

export function updateDocumentAcl(id: string, body: UpdateDocumentAclRequest) {
  return apiClient.patch<DocumentRead>(`/admin/documents/${id}`, body);
}

export function deleteDocument(id: string) {
  return apiClient.delete<void>(`/admin/documents/${id}`);
}

export function reindexDocument(id: string) {
  return apiClient.post<ReindexDocumentResponse>(`/admin/documents/${id}/reindex`);
}
