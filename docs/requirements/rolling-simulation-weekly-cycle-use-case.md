# Use Case

## 1. Use Case ID và Tên use case

**UC-002 — Thực thi một Chu kỳ (Tuần) trong Rolling Simulation**

## 2. Mô tả ngắn (mục tiêu)

Actor (Rolling Simulation Engine) thực thi đầy đủ pipeline xử lý cho **một tuần t duy nhất**, cho **một kịch bản** (baseline hoặc tối ưu): dự báo nhu cầu → tính safety stock/reorder point (chỉ kịch bản tối ưu) → xác định cửa hàng thừa/thiếu → lập kế hoạch chuyển hàng có ràng buộc (chỉ kịch bản tối ưu) → giả lập bán hàng thực tế → cập nhật tồn kho → tính KPI tuần đó. Use case này là đơn vị xử lý nội bộ, được [UC-001](UC-001-rolling-simulation-dashboard.md) gọi lặp lại N lần (một lần cho mỗi tuần, cho cả hai kịch bản) trong vòng lặp rolling simulation.

## 3. Actor chính (và actor phụ nếu có)

- **Actor chính:** Rolling Simulation Engine (module điều phối nội bộ hệ thống, thực thi pipeline theo tuần).
- **Actor phụ:** Không có actor người dùng trực tiếp. Use case này được kích hoạt bởi vòng lặp thuộc UC-001 (actor gốc gián tiếp là Portfolio Owner, người khởi chạy UC-001).

## 4. Stakeholders & mối quan tâm

| Stakeholder | Mối quan tâm |
|---|---|
| Portfolio Owner | Từng chu kỳ tuần xử lý đúng logic nghiệp vụ (BR-002, BR-006–BR-008, BR-010–BR-016, BR-019), không làm sai lệch KPI tích lũy |
| UC-001 (Rolling Simulation loop) | Nhận lại đúng cặp kết quả (tồn kho cuối tuần, KPI tuần) để dùng làm input cho tuần kế tiếp và cho tổng hợp dashboard |

## 5. Tiền điều kiện (Preconditions)

- UC-001 đã khởi tạo simulation: dữ liệu synthetic ban đầu và tham số cấu hình (Mục 7A của BRD) đã nạp.
- Trạng thái tồn kho đầu tuần t đã có sẵn — là kết quả đầu ra của UC-002 cho tuần t-1, hoặc trạng thái tồn kho ban đầu nếu t = 1.
- Kịch bản đang xử lý (baseline hoặc tối ưu) đã được UC-001 xác định trước khi gọi use case này.

## 6. Hậu điều kiện / Bảo đảm thành công (Postconditions)

- Tồn kho tại tất cả cửa hàng đã được cập nhật, phản ánh kết quả bán hàng (và chuyển hàng, nếu có) của tuần t.
- KPI của tuần t (stockout rate, excess inventory, chi phí vận chuyển, MAPE — BR-019) đã được tính và trả về cho UC-001 để tích lũy vào chuỗi kết quả theo tuần.
- Trạng thái tồn kho cuối tuần t sẵn sàng làm tiền điều kiện cho lần gọi UC-002 kế tiếp (tuần t+1).

## 7. Trigger

UC-001 gọi Rolling Simulation Engine xử lý tuần t, khi vòng lặp rolling simulation đến lượt tuần đó (bước 3 của UC-001, lặp cho từng t từ 1 đến N).

## 8. Luồng chính (Basic/Main flow)

1. Engine nhận input: chỉ số tuần **t**, trạng thái tồn kho đầu tuần, kịch bản đang xử lý (baseline hoặc tối ưu).
2. Engine chạy dự báo nhu cầu cho từng SKU/cửa hàng bằng Holt-Winters (BR-002) — kịch bản baseline dùng trung bình 90 ngày (logic v1) thay thế.
3. [Chỉ kịch bản tối ưu] Engine tính safety stock và reorder point theo service level/Z-score/lead time (BR-006, BR-007).
4. Engine xác định cửa hàng thừa/thiếu: theo reorder point/safety stock (BR-008) ở kịch bản tối ưu, theo days-of-inventory ở kịch bản baseline.
5. [Chỉ kịch bản tối ưu] Engine lập kế hoạch chuyển hàng bằng thuật toán được UC-001 chỉ định (rule-based greedy hoặc genetic algorithm), tôn trọng ràng buộc sức chứa xe, lịch giao hàng cố định, FEFO và loại trừ hàng cận hạn (BR-010, BR-011, BR-013, BR-014, BR-015, BR-016).
6. Engine giả lập bán hàng thực tế của tuần t và cập nhật tồn kho tại từng cửa hàng (áp dụng kế hoạch chuyển hàng nếu có từ bước 5).
7. Engine tính KPI của tuần t: stockout rate, excess inventory, chi phí vận chuyển, MAPE (BR-019).
8. Engine trả kết quả (trạng thái tồn kho cuối tuần t, KPI tuần t) về cho UC-001.

## 9. Luồng thay thế (Alternate flows)

- **AF-1** (tại bước 3–5): Kịch bản đang xử lý là baseline → bỏ qua hoàn toàn bước 3 (safety stock/reorder point) và bộ ràng buộc vận hành ở bước 5; phân loại thừa/thiếu (bước 4) và xử lý bán hàng dùng logic đơn giản kiểu v1, không lập kế hoạch chuyển hàng có ràng buộc.
- **AF-2** (tại bước 5): UC-001 chỉ định engine chỉ chạy một thuật toán (rule-based **hoặc** genetic algorithm) thay vì thuật toán mặc định → engine dùng đúng thuật toán được chỉ định cho toàn bộ bước 5 của tuần này.

## 10. Luồng ngoại lệ / lỗi (Exception flows)

- **EF-1** (tại bước 5): Không tìm được kế hoạch chuyển hàng nào thỏa toàn bộ ràng buộc cứng trong tuần t (ví dụ không có tuyến giao hàng hợp lệ) → engine ghi nhận "không chuyển hàng tuần t", vẫn tiếp tục bước 6–8 bình thường (bán hàng, KPI được tính trên tồn kho không có chuyển hàng), trả kết quả về cho UC-001 để tiếp tục sang tuần kế tiếp thay vì dừng toàn bộ simulation (khớp EF-2 của UC-001).
- **EF-2** (tại bước 2): Module dự báo gặp lỗi hoặc dữ liệu không đủ cho một SKU cụ thể (ví dụ SKU mới chưa có đủ lịch sử) → engine dùng fallback nhu cầu trung bình (moving average ngắn hạn) cho riêng SKU/cửa hàng đó trong tuần này, ghi log cảnh báo, tiếp tục bước 3–8 bình thường (giải quyết OQ-009).

## 11. Business rules liên quan

BR-002, BR-006, BR-007, BR-008, BR-010, BR-011, BR-013, BR-014, BR-015, BR-016, BR-019 — nguồn: `inventory-transfer-optimization-v2-BRD.md`.

## 12. Yêu cầu phi chức năng liên quan

- Thời gian xử lý một tuần phải đủ nhanh để tổng thời gian chạy N tuần nằm trong ngưỡng chấp nhận được của UC-001 (dưới 15 phút cho cả lượt chạy — xem Mục 12 của UC-001, đã giải quyết OQ-007).
- Kết quả một tuần phải tái lập được khi dùng cùng random seed, kế thừa yêu cầu tái lập của UC-001 (Mục 10 — Dependencies của BRD).

## 13. Tần suất / Giả định / Câu hỏi mở

**Tần suất:** Được gọi N lần cho mỗi kịch bản trong mỗi lượt chạy UC-001 (mặc định N = 12 tuần × 2 kịch bản = 24 lần gọi mỗi lượt full run) — không có kịch bản kích hoạt độc lập ngoài UC-001.

**Giả định:**
- Use case này luôn được gọi trong ngữ cảnh của UC-001; không có luồng khởi động độc lập.
- Việc chạy hai kịch bản (baseline, tối ưu) là hai lần gọi UC-002 tuần tự, độc lập trạng thái tồn kho với nhau (mỗi kịch bản có chuỗi tồn kho riêng) — theo giả định hợp lý từ Mục 6 (Future State) của BRD.

**Câu hỏi mở:**
- [x] OQ-009: Hành vi khi module dự báo gặp lỗi/thiếu dữ liệu (ví dụ SKU mới chưa đủ lịch sử) — **Đã giải quyết**: engine fallback về nhu cầu trung bình đơn giản (moving average ngắn hạn) cho riêng SKU/cửa hàng đó trong tuần đó, ghi log cảnh báo, không dừng simulation. Bổ sung **EF-2**: *(tại bước 2)* Dự báo lỗi/thiếu dữ liệu cho một SKU → dùng fallback moving average, ghi log, tiếp tục các bước 3–8 bình thường cho SKU đó.
- [x] OQ-010: Hai kịch bản xử lý tuần tự hay song song — **Đã giải quyết**: xử lý tuần tự (baseline trước, tối ưu sau, hoặc ngược lại) trong cùng tuần t, để đơn giản hóa (tránh phức tạp hóa bằng multiprocessing trong phạm vi demo); không ảnh hưởng kết quả nghiệp vụ vì hai kịch bản độc lập trạng thái.
