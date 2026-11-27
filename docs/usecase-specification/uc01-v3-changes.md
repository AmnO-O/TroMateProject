# UC01 Log Shared Expense: những gì cần cập nhật theo spec v3.0

Spec: [usecase-specification-v3.0.docx](usecase-specification-v3.0.docx). Xem mục 1.3 (BR02, BR03, BR10) và mục 2.1 (UC01).

Spec v3 thay đổi hai điểm liên quan đến UC01:
- **Window auto-confirm:** không còn mặc định 5 phút nữa mà do cả phòng vote ra (UC13), và creator được tắt auto-confirm cho từng khoản chi.
- **Payer:** creator luôn là payer, không còn nhập hộ người khác (BR01).

## 1. Hành vi UC01 thay đổi

| | v2.0 | v3.0 |
|---|---|---|
| Payer | Mặc định là người nhập, nhưng đổi được sang người khác (UC03b-AF06) | **Luôn là người nhập** (creator = payer), không đổi được. Nếu mô tả nói người khác trả (ví dụ "Lan trả 200k") thì TroMate từ chối và yêu cầu người trả tự nhập (UC03b-AF06 mới) |
| Window của phòng | Mặc định 5 phút; các giá trị cho phép: 5/15/30 phút, 1/6/12/24 giờ | **Không có mặc định**: phòng mới chưa có window. Giá trị do UC13 vote ra, từ **1 ngày đến 30 ngày** |
| Bước 3, summary | Chỉ có các nút Share / Edit / Cancel | Thêm **trạng thái auto-confirm** và **window của phòng**, kèm nút **Turn off auto-confirmation** |
| Auto-confirm | Luôn bật với khoản chi text | **Mặc định bật** nếu phòng có window; creator tắt được trước khi Share |
| Bước 5, tin nhắn trong group | Tag mọi người liên quan với Agree / Reject / Edit | Tag **participant** với **Agree / Reject**; creator có **Edit / Cancel expense** (BR04) |
| Bước 5, deadline | `now + window của phòng` (trừ khoản chi cần duyệt thủ công) | Chỉ tính deadline khi auto-confirm đang **bật**: `now + window của phòng` |

**Alternative flow mới:**
- **UC01-AF05 Member turns off auto-confirmation:** ở bước 4, creator bấm Turn off. Khoản chi chuyển sang duyệt thủ công, summary được cập nhật, rồi quay về bước 4.
- **UC01-AF06 Room has no auto-confirmation window:** ở bước 3, khoản chi là text nhưng phòng chưa có window. Khoản chi chuyển sang duyệt thủ công, summary báo "phòng chưa có window auto-confirm", rồi quay về bước 4.

**Post-condition:** khoản chi bật auto-confirm thì có deadline; mọi khoản chi khác được đánh dấu duyệt thủ công.

## 2. Điều kiện để có deadline (BR02)

Khoản chi có deadline khi và chỉ khi thỏa **cả ba** điều kiện:
1. Khoản chi nhập bằng **text**. Receipt, tiền điện nước và tiền nhà luôn duyệt thủ công.
2. Phòng **đã có window**.
3. Creator **không tắt** auto-confirm.

Thiếu một trong ba điều kiện thì khoản chi không có deadline (duyệt thủ công).

Window được **chốt tại lúc Share** và lưu vào khoản chi. Sau này phòng có vote ra window mới thì khoản chi đã tạo vẫn giữ window cũ (BR03).

## 3. Ngoài phạm vi UC01

- Logic vote window (UC13) và request đổi window (UC15) do người khác phụ trách. Cho đến khi UC13 xong, có thể seed window của phòng trực tiếp để test nhánh có window.
- Với UC05 Edit: khoản chi chạy lại deadline theo window đã lưu trong khoản chi, **không** theo window hiện tại của phòng. Báo người làm UC05.

## 4. Test

Test case UC01 cần thêm các trường hợp sau:
- Mô tả nói người khác trả: TroMate từ chối, không tạo khoản chi (UC03b-AF06). Test case cũ "Member changes the payer" cần bỏ hoặc viết lại.
- Phòng chưa có window: khoản chi chuyển sang duyệt thủ công (AF06).
- Creator tắt auto-confirm: khoản chi chuyển sang duyệt thủ công (AF05).
- Phòng có window 1 ngày: deadline đúng bằng thời điểm Share + 24 giờ.
- Window của phòng đổi sau khi Share: deadline của khoản chi cũ không đổi.
