import { create } from "zustand";

type ArticlesViewState = {
  status: string;
  draftSearch: string;
  search: string;
  page: number;
  pageSize: number;
  setStatus: (status: string) => void;
  setDraftSearch: (search: string) => void;
  submitSearch: () => void;
  setPage: (page: number) => void;
};

export const useArticlesViewStore = create<ArticlesViewState>((set) => ({
  status: "all",
  draftSearch: "",
  search: "",
  page: 1,
  pageSize: 20,
  setStatus: (status) => set({ status, page: 1 }),
  setDraftSearch: (draftSearch) => set({ draftSearch }),
  submitSearch: () =>
    set((state) => ({
      search: state.draftSearch,
      page: 1,
    })),
  setPage: (page) => set({ page }),
}));
