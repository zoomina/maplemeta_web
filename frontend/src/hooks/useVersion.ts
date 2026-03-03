import { createContext, useContext, useState } from 'react';

interface VersionContextValue {
  selectedVersion: string;
  setSelectedVersion: (v: string) => void;
  versions: string[];
  setVersions: (vs: string[]) => void;
  selectedType: string;
  setSelectedType: (t: string) => void;
}

export const VersionContext = createContext<VersionContextValue>({
  selectedVersion: '',
  setSelectedVersion: () => {},
  versions: [],
  setVersions: () => {},
  selectedType: '전체',
  setSelectedType: () => {},
});

export function useVersion() {
  return useContext(VersionContext);
}

export function useVersionState(): VersionContextValue {
  const [selectedVersion, setSelectedVersion] = useState('');
  const [versions, setVersions] = useState<string[]>([]);
  const [selectedType, setSelectedType] = useState('전체');
  return { selectedVersion, setSelectedVersion, versions, setVersions, selectedType, setSelectedType };
}
