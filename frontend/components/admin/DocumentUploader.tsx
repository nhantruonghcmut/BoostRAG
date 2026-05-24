'use client';

import { useCallback, useRef, useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useTranslations } from 'next-intl';
import { Loader2, Upload } from 'lucide-react';
import { toast } from 'sonner';

import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select } from '@/components/ui/select';
import { documentsApi } from '@/lib/api/documents';
import { ApiError } from '@/lib/types/api';
import { cn } from '@/lib/utils/cn';

const DOCUMENTS_QUERY_KEY = ['admin', 'documents'] as const;

function parseGroupsInput(raw: string): string[] {
  return raw
    .split(',')
    .map((g) => g.trim())
    .filter(Boolean);
}

export function DocumentUploader() {
  const t = useTranslations('admin.documents');
  const qc = useQueryClient();
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [file, setFile] = useState<File | null>(null);
  const [requiredLevel, setRequiredLevel] = useState('1');
  const [groupsInput, setGroupsInput] = useState('');
  const [isDragging, setIsDragging] = useState(false);

  const upload = useMutation({
    mutationFn: documentsApi.uploadDocument,
    onSuccess: () => {
      toast.success(t('upload.success'));
      setFile(null);
      setGroupsInput('');
      setRequiredLevel('1');
      if (fileInputRef.current) fileInputRef.current.value = '';
      qc.invalidateQueries({ queryKey: DOCUMENTS_QUERY_KEY });
    },
    onError: (error: unknown) => {
      const message = error instanceof ApiError ? error.message : t('upload.error');
      toast.error(message);
    },
  });

  const pickFile = useCallback((next: File | null) => {
    if (!next) {
      setFile(null);
      return;
    }
    setFile(next);
  }, []);

  const onDrop = useCallback(
    (event: React.DragEvent<HTMLDivElement>) => {
      event.preventDefault();
      setIsDragging(false);
      const dropped = event.dataTransfer.files.item(0);
      if (dropped) pickFile(dropped);
    },
    [pickFile],
  );

  const onSubmit = (event: React.FormEvent) => {
    event.preventDefault();
    if (!file) {
      toast.error(t('upload.noFile'));
      return;
    }
    upload.mutate({
      file,
      requiredLevel: Number(requiredLevel),
      allowedGroups: parseGroupsInput(groupsInput),
    });
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>{t('upload.title')}</CardTitle>
        <CardDescription>{t('upload.description')}</CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={onSubmit} className="space-y-5">
          <div
            role="button"
            tabIndex={0}
            onKeyDown={(event) => {
              if (event.key === 'Enter' || event.key === ' ') fileInputRef.current?.click();
            }}
            onDragOver={(event) => {
              event.preventDefault();
              setIsDragging(true);
            }}
            onDragLeave={() => setIsDragging(false)}
            onDrop={onDrop}
            onClick={() => fileInputRef.current?.click()}
            className={cn(
              'flex cursor-pointer flex-col items-center justify-center gap-3 rounded-lg border-2 border-dashed px-6 py-10 text-center transition-colors',
              isDragging ? 'border-primary bg-primary/5' : 'border-muted-foreground/25 hover:border-primary/50',
            )}
          >
            <Upload className="h-10 w-10 text-muted-foreground" aria-hidden />
            <div>
              <p className="font-medium">{t('upload.dropzone')}</p>
              <p className="text-sm text-muted-foreground">{t('upload.dropzoneHint')}</p>
            </div>
            {file && (
              <p className="text-sm text-primary">
                {file.name} ({formatBytes(file.size)})
              </p>
            )}
            <input
              ref={fileInputRef}
              type="file"
              className="hidden"
              onChange={(event) => pickFile(event.target.files?.item(0) ?? null)}
            />
          </div>

          <div className="grid gap-5 sm:grid-cols-2">
            <div className="space-y-2">
              <Label htmlFor="required-level">{t('upload.requiredLevel')}</Label>
              <Select
                id="required-level"
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
              <Label htmlFor="allowed-groups">{t('upload.allowedGroups')}</Label>
              <Input
                id="allowed-groups"
                value={groupsInput}
                onChange={(event) => setGroupsInput(event.target.value)}
                placeholder={t('upload.groupsPlaceholder')}
              />
              <p className="text-xs text-muted-foreground">{t('upload.groupsHint')}</p>
            </div>
          </div>

          <Button type="submit" disabled={upload.isPending || !file}>
            {upload.isPending && <Loader2 className="h-4 w-4 animate-spin" aria-hidden />}
            {t('upload.submit')}
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}

function formatBytes(bytes: number): string {
  if (bytes === 0) return '0 B';
  const units = ['B', 'KB', 'MB', 'GB'];
  const index = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), units.length - 1);
  const value = bytes / 1024 ** index;
  return `${value.toFixed(index === 0 ? 0 : 1)} ${units[index]}`;
}

export { DOCUMENTS_QUERY_KEY };
