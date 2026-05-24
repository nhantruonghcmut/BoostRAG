'use client';

import { useEffect, useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useTranslations } from 'next-intl';
import { Loader2 } from 'lucide-react';
import { toast } from 'sonner';

import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select } from '@/components/ui/select';
import { documentsApi } from '@/lib/api/documents';
import type { DocumentSummary } from '@/lib/types/api';
import { ApiError } from '@/lib/types/api';

import { DOCUMENTS_QUERY_KEY } from './DocumentUploader';

interface AclEditDialogProps {
  document: DocumentSummary | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

function parseGroupsInput(raw: string): string[] {
  return raw
    .split(',')
    .map((g) => g.trim())
    .filter(Boolean);
}

export function AclEditDialog({ document, open, onOpenChange }: AclEditDialogProps) {
  const t = useTranslations('admin.documents');
  const qc = useQueryClient();

  const [requiredLevel, setRequiredLevel] = useState('1');
  const [groupsInput, setGroupsInput] = useState('');

  useEffect(() => {
    if (!document) return;
    setRequiredLevel(String(document.required_level));
    setGroupsInput(document.allowed_groups.join(', '));
  }, [document]);

  const updateAcl = useMutation({
    mutationFn: (payload: { id: string; requiredLevel: number; allowedGroups: string[] }) =>
      documentsApi.updateDocumentAcl(payload.id, {
        required_level: payload.requiredLevel,
        allowed_groups: payload.allowedGroups,
      }),
    onSuccess: () => {
      toast.success(t('acl.success'));
      onOpenChange(false);
      qc.invalidateQueries({ queryKey: DOCUMENTS_QUERY_KEY });
    },
    onError: (error: unknown) => {
      const message = error instanceof ApiError ? error.message : t('acl.error');
      toast.error(message);
    },
  });

  const onSubmit = (event: React.FormEvent) => {
    event.preventDefault();
    if (!document) return;
    updateAcl.mutate({
      id: document.document_id,
      requiredLevel: Number(requiredLevel),
      allowedGroups: parseGroupsInput(groupsInput),
    });
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogClose />
        <DialogHeader>
          <DialogTitle>{t('acl.title')}</DialogTitle>
          <DialogDescription>
            {document ? t('acl.description', { name: document.name }) : t('acl.descriptionGeneric')}
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={onSubmit} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="acl-required-level">{t('upload.requiredLevel')}</Label>
            <Select
              id="acl-required-level"
              value={requiredLevel}
              onChange={(event) => setRequiredLevel(event.target.value)}
            >
              {[1, 2, 3, 4, 5].map((level) => (
                <option key={level} value={String(level)}>
                  {t('upload.levelOption', { level })}
                </option>
              ))}
            </Select>
          </div>

          <div className="space-y-2">
            <Label htmlFor="acl-allowed-groups">{t('upload.allowedGroups')}</Label>
            <Input
              id="acl-allowed-groups"
              value={groupsInput}
              onChange={(event) => setGroupsInput(event.target.value)}
              placeholder={t('upload.groupsPlaceholder')}
            />
            <p className="text-xs text-muted-foreground">{t('upload.groupsHint')}</p>
          </div>

          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
              {t('actions.cancel')}
            </Button>
            <Button type="submit" disabled={updateAcl.isPending || !document}>
              {updateAcl.isPending && <Loader2 className="h-4 w-4 animate-spin" aria-hidden />}
              {t('acl.save')}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
