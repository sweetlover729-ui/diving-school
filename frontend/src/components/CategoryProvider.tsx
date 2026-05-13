'use client';

import { createContext, useContext, useState, useEffect, useCallback, ReactNode } from 'react';
import { categoryApi } from '@/lib/api';
import type { Category } from '@/lib/types';

interface CategoryContextType {
  categories: Category[];
  currentCategoryId: number | null;
  loading: boolean;
  setCurrentCategoryId: (id: number) => void;
  currentCategory: Category | null;
  refreshCategories: () => Promise<void>;
}

const CategoryContext = createContext<CategoryContextType>({
  categories: [],
  currentCategoryId: null,
  loading: true,
  setCurrentCategoryId: () => {},
  currentCategory: null,
  refreshCategories: async () => {},
});

const STORAGE_KEY = 'adminCategoryId';

export function CategoryProvider({ children }: { children: ReactNode }) {
  const [categories, setCategories] = useState<Category[]>([]);
  const [currentCategoryId, setCurrentCategoryIdState] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);

  const refreshCategories = useCallback(async () => {
    try {
      const data = await categoryApi.list();
      const list = Array.isArray(data) ? data : [];
      setCategories(list);
      
      // 保持当前选中或恢复上次选中的分类
      setCurrentCategoryIdState(prev => {
        if (prev && list.some(c => c.id === prev)) return prev;
        const savedId = localStorage.getItem(STORAGE_KEY);
        if (savedId && list.some(c => c.id === parseInt(savedId))) return parseInt(savedId);
        return list.length > 0 ? list[0].id : null;
      });
    } catch {
      // 静默失败，由调用方处理
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refreshCategories();
  }, [refreshCategories]);

  const setCurrentCategoryId = useCallback((id: number) => {
    setCurrentCategoryIdState(id);
    localStorage.setItem(STORAGE_KEY, String(id));
  }, []);

  const currentCategory = categories.find(c => c.id === currentCategoryId) || null;

  return (
    <CategoryContext.Provider
      value={{
        categories,
        currentCategoryId,
        loading,
        setCurrentCategoryId,
        currentCategory,
        refreshCategories,
      }}
    >
      {children}
    </CategoryContext.Provider>
  );
}

export function useCategory() {
  const ctx = useContext(CategoryContext);
  if (!ctx) throw new Error('useCategory must be used within CategoryProvider');
  return ctx;
}