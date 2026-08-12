# Business Requirements Document (BRD)

## 0. Document Control

| Trường | Giá trị |
|---|---|
| Tên dự án | Inventory Transfer Optimization System v2 |
| Mã dự án | ITOS-V2 |
| Phiên bản | 1.2 |
| Ngày tạo | 2026-08-06 |
| Tác giả | Chủ dự án (Portfolio Owner) |
| Trạng thái | Draft |

**Lịch sử thay đổi**

| Phiên bản | Ngày | Người sửa | Nội dung thay đổi |
|---|---|---|---|
| 1.0 | 2026-08-06 | Chủ dự án | Khởi tạo BRD từ ghi chú yêu cầu ban đầu |
| 1.1 | 2026-08-06 | Chủ dự án | Giải quyết OQ-001 đến OQ-006 (dự án cá nhân, quyết định trực tiếp không cần khảo sát thêm); bổ sung Mục 7A tham số cấu hình |
| 1.2 | 2026-08-12 | Chủ dự án | Bổ sung BR-025, BR-026 (đặt hàng bổ sung từ nhà cung cấp) sau khi kiểm thử thực tế phát hiện hệ thống không có nguồn bổ sung tồn kho bên ngoài, khiến 2 kịch bản baseline/tối ưu hội tụ về cùng kết quả trong simulation 12 tuần |

---

## 1. Purpose (Mục đích tài liệu)

Tài liệu này xác định phạm vi, yêu cầu nghiệp vụ và tiêu chí thành công cho việc viết lại toàn bộ hệ thống **Inventory Transfer Optimization System** thành phiên bản v2. Tài liệu phục vụ:

- Chủ dự án (vừa là BA, vừa là người triển khai kỹ thuật) — dùng làm căn cứ thiết kế kiến trúc và lập kế hoạch xây dựng.
- Người xem CV/nhà tuyển dụng — hiểu được vấn đề kinh doanh mà dự án giải quyết và giá trị kỹ thuật mang lại, thông qua tài liệu và sản phẩm demo.

## 2. Business Context / Background

Hệ thống v1 là một demo tối ưu chuyển hàng tồn kho giữa các cửa hàng bán lẻ, sử dụng hai thuật toán (rule-based greedy và genetic algorithm) để đề xuất chuyển hàng dư sang cửa hàng thiếu, dựa trên dữ liệu bán hàng lịch sử và ma trận chi phí vận chuyển giả lập.

**Hạn chế của v1:**
- Phân loại thừa/thiếu chỉ dựa trên chỉ số days-of-inventory đơn giản (tồn kho / doanh số trung bình 90 ngày) — không xét đến biến động nhu cầu.
- Không có dự báo nhu cầu (demand forecasting) — chỉ lấy trung bình lịch sử.
- Không có khái niệm safety stock / reorder point theo service level.
- Không có ràng buộc vận hành thực tế (sức chứa xe, lịch giao hàng cố định, hạn sử dụng sản phẩm).
- Không có vòng đo lường hiệu quả sau khi áp dụng đề xuất chuyển hàng (không biết đề xuất có thực sự cải thiện KPI hay không).

Những hạn chế này khiến v1 chỉ dừng ở mức minh họa thuật toán, chưa thể hiện được năng lực phân tích nghiệp vụ chuỗi cung ứng ở mức sát thực tế — điều cần thiết cho mục đích portfolio/CV.

## 3. Scope

### In scope
- Viết lại toàn bộ hệ thống (không giữ song song code v1 để so sánh).
- Sinh dữ liệu synthetic có seasonality, trend, và hiệu ứng khuyến mãi cho nhu cầu bán hàng.
- Module dự báo nhu cầu bằng phương pháp thống kê cổ điển (Holt-Winters/exponential smoothing), kiến trúc cho phép bổ sung model ML (Prophet/XGBoost) như chế độ tùy chọn trong tương lai.
- Tính safety stock và reorder point theo service level (Z-score), độ lệch chuẩn nhu cầu, và lead time; bổ sung thuộc tính lead time và service level vào dữ liệu sản phẩm theo danh mục hàng.
- Ràng buộc vận hành trong lập kế hoạch chuyển hàng: sức chứa xe (thể tích/trọng lượng), lịch giao hàng cố định giữa các cặp cửa hàng, và FEFO theo hạn sử dụng — áp dụng cho cả hai thuật toán (rule-based và genetic algorithm).
- Rolling simulation nhiều chu kỳ (mặc định 12 tuần): dự báo → tính nhu cầu chuyển theo safety stock → tối ưu có ràng buộc → giả lập bán hàng thực tế → cập nhật tồn kho → đo KPI.
- Dashboard HTML tĩnh trực quan hóa KPI theo thời gian, dùng cho mục đích trình bày portfolio/CV.
- Tài liệu yêu cầu (BRD, Use Case) và kiến trúc module rõ ràng.

### Out of scope
- Tích hợp với hệ thống thật (ERP/POS) — toàn bộ dữ liệu là synthetic, không kết nối nguồn dữ liệu thật.
- Khắc phục tính non-determinism của thuật toán di truyền (genetic algorithm) — chấp nhận kết quả có thể khác nhau giữa các lần chạy.
- Triển khai production/real-time — hệ thống chạy offline theo lô (batch) để sinh dashboard tĩnh, không phục vụ truy vấn trực tuyến hay nhiều người dùng đồng thời.
- Giữ lại/chạy song song code v1 để đối chiếu.

## 4. Stakeholders

| Tên/Nhóm | Vai trò | Mối quan tâm / Trách nhiệm |
|---|---|---|
| Chủ dự án (Portfolio Owner) | Kiêm nhiệm BA, kiến trúc sư, dev | Đảm bảo hệ thống thể hiện đúng chiều sâu kỹ thuật và giá trị kinh doanh; chịu trách nhiệm toàn bộ thiết kế và triển khai |
| Nhà tuyển dụng / Người xem CV | End audience, người đánh giá | Đánh giá năng lực qua (a) chiều sâu kỹ thuật, (b) giá trị kinh doanh thể hiện bằng số liệu/biểu đồ, (c) chất lượng kiến trúc code |

> Dự án là sản phẩm cá nhân (portfolio), không có product sponsor hay ban điều hành riêng biệt.

## 5. Current State (As-Is)

Hệ thống v1 vận hành theo luồng: đọc dữ liệu bán hàng lịch sử (synthetic) và ma trận chi phí vận chuyển → tính days-of-inventory cho từng SKU tại từng cửa hàng → phân loại cửa hàng thừa/thiếu theo ngưỡng đơn giản → chạy một trong hai thuật toán (rule-based greedy hoặc genetic algorithm) để đề xuất danh sách chuyển hàng → xuất kết quả đề xuất.

**Điểm đau (pain points):**
- Ngưỡng days-of-inventory không phản ánh biến động nhu cầu thực tế (không có dự báo, không có độ lệch chuẩn nhu cầu).
- Không có cơ chế đảm bảo tồn kho an toàn trước rủi ro thiếu hàng trong thời gian chờ (lead time).
- Đề xuất chuyển hàng không tôn trọng ràng buộc vận hành thực tế (xe có thể chở quá tải, giao vào ngày không có lịch, chuyển hàng cận hạn sử dụng).
- Không có cách nào đo được đề xuất của thuật toán có thực sự cải thiện tình hình tồn kho/chi phí theo thời gian hay không.

## 6. Future State (To-Be)

Hệ thống v2 vận hành theo mô hình rolling simulation nhiều chu kỳ (tuần), mỗi chu kỳ gồm:

1. **Dự báo nhu cầu** cho từng SKU/cửa hàng bằng Holt-Winters/exponential smoothing (xét seasonality, trend), trên dữ liệu synthetic được sinh có đặc tính tương ứng.
2. **Tính safety stock và reorder point** theo công thức chuẩn (service level/Z-score, độ lệch chuẩn nhu cầu, lead time theo danh mục hàng), thay cho ngưỡng days-of-inventory.
3. **Lập kế hoạch chuyển hàng có ràng buộc**: cả rule-based greedy và genetic algorithm đều tôn trọng sức chứa xe, lịch giao hàng cố định giữa các cặp cửa hàng, và nguyên tắc FEFO/loại trừ hàng quá cận hạn.
4. **Đặt hàng bổ sung từ nhà cung cấp** cho các vị trí vẫn dưới reorder point sau khi đã chuyển hàng ngang, về đến nơi sau 1 tuần (BR-025, BR-026).
5. **Giả lập bán hàng thực tế của tuần đó**, cập nhật tồn kho.
6. **Đo KPI** (tỷ lệ hết hàng, tồn kho dư, chi phí vận chuyển, sai số dự báo MAPE) và tích lũy theo thời gian.

Kết quả cuối cùng là một dashboard HTML tĩnh minh họa xu hướng KPI qua các tuần, so sánh kịch bản có tối ưu với kịch bản baseline, dùng để trình bày trong CV/portfolio. Kiến trúc code được module hóa (forecasting, inventory policy, optimization, simulation, reporting) để dễ mở rộng — ví dụ thêm model ML dự báo sau này mà không phải viết lại toàn bộ.

## 7. Business Requirements

### Nhóm A — Dự báo nhu cầu (Demand Forecasting)

| ID | Tiêu đề | Mô tả | Ưu tiên | Lý do/Giá trị | Nguồn |
|---|---|---|---|---|---|
| BR-001 | Sinh dữ liệu bán hàng synthetic có seasonality/trend/promotion | Data generator phải sinh chuỗi bán hàng lịch sử cho từng SKU/cửa hàng có thành phần mùa vụ (seasonality), xu hướng (trend), và hiệu ứng khuyến mãi (promotion) rõ ràng, có thể kiểm chứng bằng phân rã chuỗi thời gian | Must | Không có đặc tính này thì mô hình dự báo không có gì để dự báo có ý nghĩa | Ghi chú yêu cầu |
| BR-002 | Dự báo nhu cầu bằng Holt-Winters/exponential smoothing | Module dự báo tính giá trị nhu cầu kỳ vọng cho từng SKU/cửa hàng theo phương pháp Holt-Winters (triple exponential smoothing), xét cả seasonality và trend | Must | Thay thế phương pháp trung bình 90 ngày hiện tại, phản ánh đúng bản chất chuỗi thời gian có mùa vụ | Ghi chú yêu cầu |
| BR-003 | Kiến trúc forecasting hỗ trợ pluggable model | Module dự báo được thiết kế theo interface trừu tượng (strategy pattern), cho phép thêm model khác (Prophet, XGBoost) như một chế độ lựa chọn mà không cần sửa đổi các module khác (inventory policy, optimization, simulation) | Should | Cho phép mở rộng năng lực kỹ thuật sau này, thể hiện chất lượng kiến trúc trong portfolio | Ghi chú yêu cầu |

### Nhóm B — Safety Stock & Reorder Point

| ID | Tiêu đề | Mô tả | Ưu tiên | Lý do/Giá trị | Nguồn |
|---|---|---|---|---|---|
| BR-004 | Bổ sung lead time theo danh mục hàng | Data model sản phẩm có thêm thuộc tính lead time (thời gian chờ hàng về), gán giá trị theo từng danh mục hàng | Must | Là input bắt buộc cho công thức safety stock/reorder point | Ghi chú yêu cầu |
| BR-005 | Bổ sung service level mục tiêu theo danh mục hàng | Data model sản phẩm có thêm thuộc tính service level mục tiêu, gán theo từng danh mục hàng, dùng để tra Z-score | Must | Là input bắt buộc cho công thức safety stock | Ghi chú yêu cầu — giá trị cụ thể: xem **Mục 7A.3** |
| BR-006 | Tính safety stock theo công thức chuẩn | Hệ thống tính safety stock = Z(service level) × độ lệch chuẩn nhu cầu × căn bậc hai(lead time), theo từng SKU/cửa hàng | Must | Thay thế ngưỡng days-of-inventory bằng cơ sở thống kê chuẩn | Ghi chú yêu cầu |
| BR-007 | Tính reorder point | Hệ thống tính reorder point = nhu cầu trung bình trong lead time + safety stock, theo từng SKU/cửa hàng | Must | Là ngưỡng kích hoạt nhu cầu bổ sung/chuyển hàng, thay cho ngưỡng days-of-inventory | Ghi chú yêu cầu |
| BR-008 | Phân loại thừa/thiếu theo reorder point/safety stock | Việc phân loại cửa hàng thừa hàng/thiếu hàng dựa trên vị trí tồn kho hiện tại so với reorder point và safety stock, không còn dùng ngưỡng days-of-inventory đơn giản của v1 | Must | Là thay đổi cốt lõi so với v1, phản ánh đúng rủi ro thiếu hàng | Ghi chú yêu cầu |
| BR-025 | Đặt hàng bổ sung từ nhà cung cấp khi chạm reorder point | Khi tồn kho một SKU/cửa hàng (sau khi đã tính cả kế hoạch chuyển hàng ngang) thấp hơn reorder point, hệ thống tự động đặt hàng bổ sung từ nhà cung cấp (giả lập), đủ để đưa tồn kho lên mức mục tiêu = 2 × reorder point (nhất quán với ngưỡng surplus ở BR-008) | Must | Phát hiện qua kiểm thử thực tế v2 (2026-08-12): nếu chỉ chuyển hàng ngang giữa các cửa hàng mà không có nguồn bổ sung từ bên ngoài, tổng tồn kho toàn hệ thống là hữu hạn và sẽ cạn kiệt đồng loạt trong vài tuần đầu của rolling simulation 12 tuần, khiến 2 kịch bản baseline/tối ưu cho kết quả gần như giống hệt nhau — không thể hiện được giá trị của forecasting/safety stock/optimization. Đây cũng là bản chất đúng của reorder point (vốn dùng để kích hoạt đặt hàng, không chỉ để phân loại) | Kiểm thử thực tế, được chủ dự án xác nhận bổ sung |
| BR-026 | Độ trễ giao hàng bổ sung xấp xỉ 1 chu kỳ tuần | Hàng đặt bổ sung ở BR-025 được giả lập về đến nơi sau đúng 1 tuần (chu kỳ simulation kế tiếp), không mô hình hóa chi tiết theo từng ngày lead time | Should | Đơn giản hóa hợp lý: toàn bộ lead_time_days theo danh mục (Mục 7A) đều ≤ 7 ngày — nằm gọn trong 1 chu kỳ tuần của simulation (đã là đơn vị thời gian nhỏ nhất của UC-002), không cần theo dõi pipeline đặt hàng theo ngày | Quyết định kỹ thuật khi triển khai |

### Nhóm C — Ràng buộc vận hành thực tế

| ID | Tiêu đề | Mô tả | Ưu tiên | Lý do/Giá trị | Nguồn |
|---|---|---|---|---|---|
| BR-009 | Bổ sung thể tích/trọng lượng theo SKU | Data model sản phẩm có thêm thuộc tính thể tích và trọng lượng đơn vị | Must | Là input bắt buộc để tính ràng buộc sức chứa xe | Ghi chú yêu cầu |
| BR-010 | Ràng buộc sức chứa xe | Kế hoạch chuyển hàng không được vượt quá sức chứa xe (giới hạn thể tích và/hoặc trọng lượng) trên mỗi chuyến vận chuyển | Must | Phản ánh giới hạn vận hành thực tế mà v1 bỏ qua | Ghi chú yêu cầu — giá trị cụ thể: xem **Mục 7A.2** |
| BR-011 | Ràng buộc lịch giao hàng cố định | Kế hoạch chuyển hàng chỉ được thực hiện vào những ngày có lịch giao hàng cố định giữa cặp cửa hàng nguồn-đích tương ứng | Must | Phản ánh ràng buộc logistics thực tế | Ghi chú yêu cầu — giá trị cụ thể: xem **Mục 7A.2** |
| BR-012 | Bổ sung hạn sử dụng theo lô hàng | Data model tồn kho có thêm thuộc tính hạn sử dụng (expiry date) ở cấp độ lô hàng (batch) | Must | Là input bắt buộc để áp dụng FEFO | Ghi chú yêu cầu |
| BR-013 | Áp dụng FEFO khi chọn lô chuyển | Khi lập kế hoạch chuyển hàng, hệ thống ưu tiên chọn lô hàng có hạn sử dụng gần nhất trước (First-Expired-First-Out) | Must | Giảm rủi ro hủy hàng do hết hạn tại cửa hàng nguồn | Ghi chú yêu cầu |
| BR-014 | Loại trừ hàng quá cận hạn | Hệ thống không đưa vào kế hoạch chuyển các lô hàng có hạn sử dụng còn lại dưới ngưỡng tối thiểu quy định | Must | Tránh chuyển hàng sắp hết hạn đến nơi không kịp bán | Ghi chú yêu cầu — ngưỡng cụ thể: xem **Mục 7A.2** |
| BR-015 | Rule-based greedy tôn trọng ràng buộc vận hành | Thuật toán rule-based greedy khi sinh đề xuất chuyển hàng phải tuân thủ đầy đủ BR-010, BR-011, BR-013, BR-014 | Must | Đảm bảo tính khả thi thực tế của đề xuất từ cả hai thuật toán | Ghi chú yêu cầu |
| BR-016 | Genetic algorithm tôn trọng ràng buộc vận hành | Thuật toán genetic algorithm khi sinh đề xuất chuyển hàng phải tuân thủ đầy đủ BR-010, BR-011, BR-013, BR-014 (thông qua ràng buộc cứng hoặc cơ chế phạt trong hàm fitness) | Must | Đảm bảo tính khả thi thực tế của đề xuất từ cả hai thuật toán | Ghi chú yêu cầu |

### Nhóm D — Vòng phản hồi đo hiệu quả (Feedback Loop)

| ID | Tiêu đề | Mô tả | Ưu tiên | Lý do/Giá trị | Nguồn |
|---|---|---|---|---|---|
| BR-017 | Rolling simulation nhiều chu kỳ | Hệ thống mô phỏng liên tiếp nhiều chu kỳ tuần (mặc định 12 tuần, có thể cấu hình số tuần) | Must | Cho phép quan sát xu hướng cải thiện theo thời gian, không chỉ một lần chạy tĩnh | Ghi chú yêu cầu |
| BR-018 | Pipeline đầy đủ mỗi chu kỳ | Mỗi tuần trong simulation thực hiện tuần tự: dự báo nhu cầu → tính nhu cầu chuyển theo safety stock/reorder point → tối ưu kế hoạch chuyển có ràng buộc → giả lập bán hàng thực tế tuần đó → cập nhật tồn kho | Must | Đây là cơ chế cốt lõi tạo ra vòng phản hồi đo hiệu quả | Ghi chú yêu cầu |
| BR-019 | Đo KPI theo tuần | Hệ thống tính và lưu lại theo từng tuần: tỷ lệ hết hàng (stockout rate), tồn kho dư (excess inventory), chi phí vận chuyển, sai số dự báo (MAPE) | Must | Là cơ sở định lượng để chứng minh giá trị kinh doanh | Ghi chú yêu cầu |
| BR-020 | So sánh với kịch bản baseline | Simulation chạy song song một kịch bản baseline không áp dụng tối ưu (hoặc theo logic đơn giản kiểu v1), để đối chiếu KPI với kịch bản có tối ưu trong cùng bộ dữ liệu | Must | Là bằng chứng "trước/sau" cần thiết cho mục đích trình bày CV | Ghi chú yêu cầu |
| BR-021 | Dashboard HTML tĩnh | Hệ thống xuất ra một dashboard dạng file HTML tĩnh, hiển thị biểu đồ các KPI (BR-019) theo tuần, cho cả kịch bản baseline và kịch bản tối ưu | Must | Là sản phẩm trực quan chính dùng để trình bày trong CV/portfolio | Ghi chú yêu cầu |

### Nhóm E — Kiến trúc & phạm vi viết lại

| ID | Tiêu đề | Mô tả | Ưu tiên | Lý do/Giá trị | Nguồn |
|---|---|---|---|---|---|
| BR-022 | Viết lại toàn bộ, không giữ song song v1 | Toàn bộ codebase được viết mới; không giữ lại code v1 để chạy song song so sánh | Must | Theo đúng ràng buộc dự án đã nêu | Ghi chú yêu cầu |
| BR-023 | Kiến trúc module hóa | Codebase được tách thành các module độc lập tương ứng với từng năng lực nghiệp vụ: sinh dữ liệu, dự báo, chính sách tồn kho (safety stock/reorder point), tối ưu vận chuyển, mô phỏng rolling simulation, và báo cáo/dashboard | Should | Thể hiện chất lượng kiến trúc code cho người xem CV | Ghi chú yêu cầu |
| BR-024 | Không tích hợp hệ thống thật | Toàn bộ dữ liệu đầu vào (bán hàng, tồn kho, sản phẩm, vận chuyển) là dữ liệu synthetic; hệ thống không kết nối API/DB của bất kỳ hệ thống ERP/POS thật nào | Must | Theo đúng ràng buộc dự án đã nêu | Ghi chú yêu cầu |

## 7A. Tham số Cấu hình Dự án (Resolved Configuration Parameters)

Các tham số dưới đây giải quyết OQ-001, OQ-003, OQ-004, OQ-006 (xem Mục 13). Vì đây là dự án cá nhân/demo, giá trị được chọn theo kinh nghiệm ngành bán lẻ điển hình để đảm bảo tính minh họa rõ ràng, không dựa trên khảo sát thực tế — có thể điều chỉnh trong quá trình phát triển nếu cần.

### 7A.1 Quy mô dữ liệu (giải quyết OQ-001)

| Thực thể | Quy mô |
|---|---|
| Cửa hàng | 20 cửa hàng, 3 thành phố (Hà Nội, TP.HCM, Đà Nẵng) |
| Sản phẩm (SKU) | 30 sản phẩm |
| Danh mục hàng | 5 danh mục: Thiết yếu, Đồ uống, Đồ khô, Đông lạnh, Gia dụng |
| Lịch sử bán hàng | 52 tuần (364 ngày) dữ liệu synthetic — đủ để Holt-Winters học được mùa vụ theo tuần và xu hướng, trước khi bước vào 12 tuần rolling simulation forward |

### 7A.2 Ràng buộc vận hành (giải quyết OQ-003)

| Ràng buộc | Giá trị |
|---|---|
| Sức chứa xe/chuyến | 500 kg **và** 2 m³ (giới hạn theo ngưỡng nào đạt trước) |
| Lịch giao hàng | Mỗi cặp cửa hàng có lịch cố định 2 ngày/tuần, sinh ngẫu nhiên nhưng cố định theo seed cho từng tuyến |
| Ngưỡng cận hạn loại trừ (BR-014) | Lô hàng còn hạn sử dụng < 7 ngày không được đưa vào kế hoạch chuyển |

### 7A.3 Service level theo danh mục hàng (giải quyết OQ-006)

| Danh mục | Service level mục tiêu | Z-score |
|---|---|---|
| Thiết yếu | 98% | 2.05 |
| Đồ uống, Đồ khô | 95% | 1.65 |
| Đông lạnh | 95% | 1.65 |
| Gia dụng | 90% | 1.28 |

### 7A.4 Công nghệ triển khai (giải quyết OQ-004)

| Thành phần | Lựa chọn |
|---|---|
| Ngôn ngữ | Python 3.11+ |
| Forecasting | statsmodels (Holt-Winters / ExponentialSmoothing) |
| Rule-based & Genetic Algorithm | Tự viết thuần Python/NumPy (kế thừa phong cách v1, dễ tùy biến ràng buộc/hàm fitness) |
| Data generation | pandas, NumPy |
| Dashboard | Plotly, xuất 1 file HTML tĩnh tự chứa (self-contained), không cần server |
| Testing | pytest |

## 8. Assumptions (Giả định)

- Người dùng cuối của sản phẩm hoàn thiện (dashboard + code) là người xem CV/nhà tuyển dụng, không phải người vận hành nghiệp vụ thật — do đó không cần các yêu cầu về UX vận hành hàng ngày (đăng nhập, phân quyền, đa người dùng).
- Dữ liệu synthetic được sinh ra một lần (hoặc theo seed cố định) đủ để minh họa các đặc tính seasonality/trend/promotion mà không cần xác thực với dữ liệu thật.
- Toàn bộ simulation chạy offline/batch, không có yêu cầu về thời gian phản hồi thời gian thực.
- Kiến trúc pluggable cho model ML (Prophet/XGBoost) chỉ cần chuẩn bị interface, không bắt buộc phải cài đặt các model này trong phạm vi v2 hiện tại.

## 9. Constraints (Ràng buộc)

- Không tích hợp hệ thống thật (ERP/POS) — chỉ dùng dữ liệu giả lập.
- Không cần khắc phục tính non-determinism của thuật toán di truyền.
- Viết lại toàn bộ, không giữ code v1 song song.
- Là dự án cá nhân (portfolio) — nguồn lực triển khai giới hạn ở một người.

## 10. Dependencies (Phụ thuộc)

- statsmodels — Holt-Winters/ExponentialSmoothing cho module dự báo. Xem Mục 7A.4.
- Plotly — dựng biểu đồ và xuất dashboard HTML tĩnh tự chứa. Xem Mục 7A.4.
- Bộ sinh số ngẫu nhiên có kiểm soát seed để đảm bảo khả năng tái lập kết quả demo, đặc biệt với genetic algorithm (không bắt buộc khắc phục non-determinism, nhưng seed cố định giúp demo nhất quán).

## 11. Risks

| Rủi ro | Ảnh hưởng | Khả năng xảy ra | Biện pháp giảm thiểu |
|---|---|---|---|
| Non-determinism của genetic algorithm khiến kết quả demo không tái lập được giữa các lần chạy | Trung bình | Cao | Cố định random seed cho các lần chạy dùng để trình bày/screenshot; không cần khắc phục triệt để theo ràng buộc dự án |
| Dữ liệu synthetic không đủ chân thực (seasonality/trend/promotion quá giả tạo) khiến dự báo/simulation mất ý nghĩa minh họa | Cao | Trung bình | Thiết kế data generator có tham số kiểm soát được và review trực quan (plot) trước khi dùng cho pipeline |
| Interface pluggable cho model ML thiết kế chưa tốt ngay từ đầu, gây khó mở rộng sau này | Trung bình | Trung bình | Áp dụng abstraction rõ ràng (ví dụ strategy pattern) cho module dự báo ngay từ v2 |
| Rolling simulation 12 tuần kết hợp genetic algorithm chạy chậm, ảnh hưởng khả năng demo | Thấp | Trung bình | Giới hạn tham số GA (population size, số thế hệ) và đo thời gian chạy trong quá trình phát triển |

## 12. Success Criteria / KPIs

- Có đầy đủ tài liệu yêu cầu: BRD (tài liệu này) và Use Case.
- Kiến trúc module rõ ràng theo BR-023 (forecasting, inventory policy, optimization, simulation, reporting tách biệt).
- Rolling simulation chạy hết 12 tuần không lỗi, tạo ra dữ liệu KPI cho cả kịch bản baseline và kịch bản tối ưu.
- Dashboard HTML tĩnh xuất ra thành công, hiển thị biểu đồ KPI (stockout rate, excess inventory, chi phí vận chuyển, MAPE) theo tuần, so sánh baseline vs tối ưu.
- Mức cải thiện KPI mục tiêu (giải quyết OQ-002) — mang tính định hướng trình bày, không phải cam kết cứng do bản chất stochastic của simulation/genetic algorithm:
  - Stockout rate: giảm ≥ 30% so với baseline sau 12 tuần.
  - Tồn kho dư (excess inventory value): giảm ≥ 20% so với baseline.
  - Tổng chi phí (vận chuyển + chi phí cơ hội do stockout/tồn kho dư): giảm ròng ≥ 15% so với baseline.
  - Sai số dự báo (MAPE) trung bình toàn hệ thống: dưới 20%.
  - Nếu một chỉ tiêu không đạt ngưỡng trên nhưng xu hướng cải thiện nhất quán và giải thích được qua các tuần, vẫn coi là đạt tiêu chí thành công cho mục đích demo/portfolio.

## 13. Open Questions

Toàn bộ Open Questions dưới đây đã được chủ dự án quyết định trực tiếp (dự án cá nhân/demo, không cần khảo sát thêm).

- [x] OQ-001: Quy mô dữ liệu giả lập — **Đã giải quyết**: 20 cửa hàng / 30 SKU / 5 danh mục / 52 tuần lịch sử bán hàng. Xem Mục 7A.1.
- [x] OQ-002: Ngưỡng cải thiện KPI mục tiêu — **Đã giải quyết**: xem Mục 12 (Success Criteria) — ngưỡng mang tính định hướng trình bày, không phải cam kết cứng.
- [x] OQ-003: Giá trị ràng buộc vận hành (sức chứa xe, lịch giao hàng, ngưỡng cận hạn) — **Đã giải quyết**: xem Mục 7A.2.
- [x] OQ-004: Công nghệ/stack triển khai — **Đã giải quyết**: xem Mục 7A.4.
- [x] OQ-005: Thời hạn hoàn thành dự án — **Đã giải quyết**: không có deadline cứng từ bên ngoài (dự án cá nhân); mốc tự đặt tham khảo 3–4 tuần làm việc bán thời gian, có thể điều chỉnh khi lập kế hoạch triển khai chi tiết.
- [x] OQ-006: Service level theo danh mục hàng — **Đã giải quyết**: xem Mục 7A.3.

## 14. Sign-off

| Tên | Vai trò | Chữ ký | Ngày |
|---|---|---|---|
| | Chủ dự án (Portfolio Owner) | | |
