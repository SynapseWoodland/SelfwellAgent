import { chooseSingleImage, type PickedImage } from '../../utils/picker';
import {
  presignAndUploadOneForAssistant,
  type BodyPart,
  type UploadedPhoto,
} from '../../utils/upload-helper';
import { post } from '../../utils/request';
import { countFilledFields, readUserProfile } from '../../utils/profile-storage';

type MiniEvent = { currentTarget: { dataset: Record<string, unknown> } };

interface UploadSlot {
  label: string;
  bodyPart: BodyPart;
  filled: boolean;
  filledUrl: string;
  picked: PickedImage | null;
}

interface SelectableOption {
  value: string;
  selected: boolean;
}

interface AssistantSessionResponse {
  session_id?: string;
  id?: string;
  stream_url?: string;
}

const DEFAULT_STREAM_PATH = (sessionId: string) =>
  `/assistant/sessions/${encodeURIComponent(sessionId)}/stream`;

Page({
  data: {
    slots: [
      { label: '额头', bodyPart: 'head', filled: false, filledUrl: '', picked: null },
      { label: '面颊', bodyPart: 'face', filled: false, filledUrl: '', picked: null },
      { label: '颈部', bodyPart: 'shoulder_neck', filled: false, filledUrl: '', picked: null },
    ] as UploadSlot[],
    body_parts: ['额头', '面颊', '颈部', 'T 区', 'U 区'].map((value) => ({
      value,
      selected: false,
    })) as SelectableOption[],
    age_ranges: ['<18', '18-24', '25-34', '35-44', '45-54', '55+'].map((value) => ({
      value,
      selected: false,
    })) as SelectableOption[],
    profileFilledCount: 0,
    photoFilledCount: 0,
    uploadProgress: 0,
    uploading: false,
  },

  onLoad() {
    this.setData({ profileFilledCount: countFilledFields(readUserProfile()) });
  },

  onNavBack() {
    wx.navigateBack({ delta: 1 });
  },

  async onTapSlot(event: MiniEvent) {
    if (this.data.uploading) return;
    const index = Number((event.currentTarget.dataset as { index?: number }).index);
    if (!Number.isInteger(index) || index < 0 || index >= this.data.slots.length) return;
    try {
      const picked = await chooseSingleImage({ sourceType: ['album', 'camera'] });
      const slots = this.data.slots.map((slot: UploadSlot, slotIndex: number) =>
        slotIndex === index
          ? { ...slot, filled: true, filledUrl: picked.path, picked }
          : slot,
      );
      this.setData({
        slots,
        photoFilledCount: slots.filter((slot: UploadSlot) => slot.filled).length,
      });
    } catch (error) {
      const message = error instanceof Error ? error.message : '选图失败，请重试';
      if (!message.includes('cancel')) wx.showToast({ title: message, icon: 'none' });
    }
  },

  onToggleBodyPart(event: MiniEvent) {
    const value = String((event.currentTarget.dataset as { value?: string }).value ?? '');
    this.setData({
      body_parts: this.data.body_parts.map((option: SelectableOption) =>
        option.value === value ? { ...option, selected: !option.selected } : option,
      ),
    });
  },

  onSelectAge(event: MiniEvent) {
    const value = String((event.currentTarget.dataset as { value?: string }).value ?? '');
    this.setData({
      age_ranges: this.data.age_ranges.map((option: SelectableOption) => ({
        ...option,
        selected: option.value === value,
      })),
    });
  },

  async onStartAnalyze() {
    if (this.data.uploading) return;
    const filledSlots = this.data.slots.filter(
      (slot: UploadSlot): slot is UploadSlot & { picked: PickedImage } => slot.filled && slot.picked !== null,
    );
    if (filledSlots.length !== 3) {
      wx.showToast({ title: '请上传额头、面颊、颈部 3 张照片', icon: 'none' });
      return;
    }
    if (!this.data.body_parts.some((option: SelectableOption) => option.selected)) {
      wx.showToast({ title: '请至少选择一个关注部位', icon: 'none' });
      return;
    }
    if (!this.data.age_ranges.some((option: SelectableOption) => option.selected)) {
      wx.showToast({ title: '请选择年龄段', icon: 'none' });
      return;
    }

    this.setData({ uploading: true, uploadProgress: 0 });
    try {
      const uploaded: UploadedPhoto[] = [];
      for (let index = 0; index < filledSlots.length; index += 1) {
        const slot = filledSlots[index];
        uploaded.push(await presignAndUploadOneForAssistant(slot.picked, slot.bodyPart));
        this.setData({ uploadProgress: Math.round(((index + 1) / filledSlots.length) * 100) });
      }
      const session: AssistantSessionResponse = await post<AssistantSessionResponse>('/assistant/sessions', {
        entry_card: 'smart_analyze',
        primary_intent: 'smart_analyze',
      }).catch((): AssistantSessionResponse => ({ session_id: `mock_${Date.now()}` }));
      const sessionId = session.session_id ?? session.id ?? `mock_${Date.now()}`;
      const streamUrl = session.stream_url ?? DEFAULT_STREAM_PATH(sessionId);
      // PR-Contract-Fix C-2:C-1 后端返回的 report_id 写入 cache,
      // 让 diagnosis-report-v2.onGeneratePlan 能取到并传给 POST /plans/generate。
      const reportId = (session as { report_id?: string }).report_id ?? '';
      wx.setStorageSync('diagnosis_v2_payload', {
        session_id: sessionId,
        report_id: reportId,
        image_keys: uploaded.map((item) => item.objectKey),
        body_parts: uploaded.map((item) => item.bodyPart),
        focus_parts: this.data.body_parts.filter((item: SelectableOption) => item.selected).map((item: SelectableOption) => item.value),
        age_range: this.data.age_ranges.find((item: SelectableOption) => item.selected)?.value ?? '',
        profile_count: this.data.profileFilledCount,
      });
      wx.redirectTo({
        url: `/pages/diagnosis-loading-v2/index?id=${encodeURIComponent(sessionId)}&stream_url=${encodeURIComponent(streamUrl)}`,
      });
    } catch (error) {
      wx.showToast({
        title: error instanceof Error ? error.message : '上传失败，请重试',
        icon: 'none',
      });
    } finally {
      this.setData({ uploading: false });
    }
  },
});
