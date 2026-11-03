import SwiftUI
import AppKit
import Foundation
import UniformTypeIdentifiers

enum Attendance: String, Codable, CaseIterable, Identifiable {
    case worked = "Đi làm"
    case dayOff = "Nghỉ"
    case paidLeave = "Nghỉ phép hưởng lương"
    case absent = "Vắng mặt"
    var id: String { rawValue }
}
struct WorkEntry: Codable {
    var status: Attendance = .worked
    var start: String = "08:00"
    var end: String = "17:00"
    var breakMinutes: Int = 60
    var note: String = ""
}
struct Employee: Codable, Identifiable {
    var id: UUID = UUID()
    var name: String = "Nhân viên 1"
    var monthlySalary: Double = 205_000
    var standardDays: Int = 26
    var standardHours: Double = 8
    var overtimeMultiplier: Double = 1.25
    var entries: [String: WorkEntry] = [:]
}
struct AppData: Codable {
    var employees: [Employee]
    var selectedID: UUID?
}
struct LegacyEntry: Codable {
    var start: String
    var end: String
    var breakMinutes: Int
    var off: Bool
    var note: String
}
struct LegacyData: Codable {
    var shifts: [String: LegacyEntry]
    var rate: Double
    var multiplier: Double
}

@MainActor final class Timesheet: ObservableObject {
    @Published var employees: [Employee] = []
    @Published var selectedID: UUID?
    @Published var errorMessage: String?
    private let folder = FileManager.default.homeDirectoryForCurrentUser
        .appendingPathComponent("Library/Application Support/ChamCongMac", isDirectory: true)
    private var dataURL: URL { folder.appendingPathComponent("data-v2.json") }
    init() {
        if let raw = try? Data(contentsOf: dataURL),
           let saved = try? JSONDecoder().decode(AppData.self, from: raw),
           !saved.employees.isEmpty {
            employees = saved.employees
            selectedID = saved.selectedID
        } else {
            var first = Employee(name: "Tôi")
            let oldURL = folder.appendingPathComponent("data.json")
            if let raw = try? Data(contentsOf: oldURL),
               let legacy = try? JSONDecoder().decode(LegacyData.self, from: raw) {
                first.overtimeMultiplier = legacy.multiplier
                for (key, old) in legacy.shifts {
                    first.entries[key] = WorkEntry(status: old.off ? .dayOff : .worked,
                                                   start: old.start, end: old.end,
                                                   breakMinutes: old.breakMinutes, note: old.note)
                }
            }
            employees = [first]
            selectedID = first.id
            save()
        }
        if !employees.contains(where: { $0.id == selectedID }) {
            selectedID = employees.first?.id
        }
    }
    var selected: Employee? { employees.first(where: { $0.id == selectedID }) }
    var selectedIndex: Int? { employees.firstIndex(where: { $0.id == selectedID }) }
    func save() {
        do {
            try FileManager.default.createDirectory(at: folder, withIntermediateDirectories: true)
            let contents = try JSONEncoder().encode(AppData(employees: employees, selectedID: selectedID))
            try contents.write(to: dataURL, options: .atomic)
        } catch { errorMessage = "Không lưu được dữ liệu: \(error.localizedDescription)" }
    }
    func addEmployee(name: String) {
        let name = name.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !name.isEmpty else { return }
        let employee = Employee(name: name)
        employees.append(employee)
        selectedID = employee.id
        save()
    }
    func updateEmployee(name: String, salary: Double, days: Int, hours: Double, multiplier: Double) {
        guard let index = selectedIndex else { return }
        let cleanName = name.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !cleanName.isEmpty, salary >= 0, days > 0, hours > 0, multiplier >= 1 else {
            errorMessage = "Kiểm tra lại tên, mức lương, ngày công và hệ số tăng ca."
            return
        }
        employees[index].name = cleanName
        employees[index].monthlySalary = salary
        employees[index].standardDays = days
        employees[index].standardHours = hours
        employees[index].overtimeMultiplier = multiplier
        save()
    }
    func deleteSelected() {
        guard employees.count > 1, let id = selectedID else { return }
        employees.removeAll(where: { $0.id == id })
        selectedID = employees.first?.id
        save()
    }
    func entry(for date: Date) -> WorkEntry? { selected?.entries[key(date)] }
    func setEntry(_ entry: WorkEntry?, for date: Date) {
        guard let index = selectedIndex else { return }
        let k = key(date)
        if let entry { employees[index].entries[k] = entry }
        else { employees[index].entries.removeValue(forKey: k) }
        save()
    }
    func key(_ date: Date) -> String {
        date.formatted(.iso8601.year().month().day().dateSeparator(.dash))
    }
    func hours(_ entry: WorkEntry) -> Double {
        guard entry.status == .worked else { return 0 }
        func minutes(_ input: String) -> Int? {
            let parts = input.split(separator: ":").compactMap { Int($0) }
            guard parts.count == 2, (0...23).contains(parts[0]), (0...59).contains(parts[1]) else { return nil }
            return parts[0] * 60 + parts[1]
        }
        guard let start = minutes(entry.start), let end = minutes(entry.end) else { return 0 }
        let elapsed = end > start ? end - start : end + 24 * 60 - start
        return Double(max(0, elapsed - entry.breakMinutes)) / 60
    }
    func summary(for dates: [Date]) -> (days: Int, leave: Int, hours: Double, overtime: Double, pay: Double) {
        guard let e = selected else { return (0, 0, 0, 0, 0) }
        var days = 0, leave = 0
        var hours = 0.0, overtime = 0.0
        for date in dates {
            guard let entry = e.entries[key(date)] else { continue }
            switch entry.status {
            case .worked:
                days += 1
                let duration = self.hours(entry)
                hours += duration
                overtime += max(0, duration - e.standardHours)
            case .paidLeave: leave += 1
            case .dayOff, .absent: break
            }
        }
        let daily = e.monthlySalary / Double(max(1, e.standardDays))
        let hourly = daily / max(0.5, e.standardHours)
        let pay = (Double(days + leave) * daily) + (overtime * hourly * e.overtimeMultiplier)
        return (days, leave, hours, overtime, pay)
    }
    func exportCSV(for dates: [Date], month: Date) {
        guard let employee = selected else { return }
        func quote(_ s: String) -> String { "\"" + s.replacingOccurrences(of: "\"", with: "\"\"") + "\"" }
        var lines = ["Ngày,Nhân viên,Trạng thái,Bắt đầu,Kết thúc,Nghỉ giữa ca (phút),Giờ làm,Ghi chú"]
        for day in dates {
            let key = self.key(day)
            guard let entry = employee.entries[key] else { continue }
            let row = [key, employee.name, entry.status.rawValue, entry.start, entry.end,
                       String(entry.breakMinutes), String(format: "%.2f", hours(entry)), entry.note]
            lines.append(row.map(quote).joined(separator: ","))
        }
        let csv = "\u{FEFF}" + lines.joined(separator: "\r\n") + "\r\n"
        let panel = NSSavePanel()
        panel.allowedContentTypes = [.commaSeparatedText]
        panel.canCreateDirectories = true
        panel.nameFieldStringValue = "ChamCong-\(key(month).prefix(7))-\(employee.name).csv"
        if panel.runModal() == .OK, let url = panel.url {
            do { try csv.write(to: url, atomically: true, encoding: .utf8) }
            catch { errorMessage = "Không xuất được CSV: \(error.localizedDescription)" }
        }
    }
}
struct ContentView: View {
    @StateObject private var model = Timesheet()
    @State private var month = Calendar.current.date(from: Calendar.current.dateComponents([.year, .month], from: Date()))!
    @State private var selectedDate = Date()
    @State private var draft = WorkEntry()
    @State private var isDayEditorOpen = false
    @State private var isSettingsOpen = false
    @State private var isNewEmployeeOpen = false
    @State private var isDeleteConfirmationOpen = false
    @State private var newEmployeeName = ""
    @State private var editName = ""
    @State private var editSalary = 205_000.0
    @State private var editDays = 26
    @State private var editHours = 8.0
    @State private var editMultiplier = 1.25
    private let calendar = Calendar.current
    private var dates: [Date] {
        guard let range = calendar.range(of: .day, in: .month, for: month) else { return [] }
        return range.compactMap { calendar.date(byAdding: .day, value: $0 - 1, to: month) }
    }
    private var dayOffset: Int { (calendar.component(.weekday, from: month) + 5) % 7 }
    var body: some View {
        HStack(spacing: 0) {
            employeeSidebar
            Divider()
            mainPanel
        }
        .frame(minWidth: 970, minHeight: 750)
        .sheet(isPresented: $isNewEmployeeOpen) {
            VStack(alignment: .leading, spacing: 15) {
                Text("Thêm nhân viên").font(.title2.bold())
                TextField("Tên nhân viên", text: $newEmployeeName)
                HStack {
                    Spacer()
                    Button("Hủy") { isNewEmployeeOpen = false }
                    Button("Thêm") {
                        model.addEmployee(name: newEmployeeName)
                        isNewEmployeeOpen = false
                    }.buttonStyle(.borderedProminent)
                        .disabled(newEmployeeName.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty)
                }
            }.padding(24).frame(width: 410)
        }
        .sheet(isPresented: $isSettingsOpen) { settingsSheet }
        .sheet(isPresented: $isDayEditorOpen) { dayEditor }
        .confirmationDialog("Xóa nhân viên?", isPresented: $isDeleteConfirmationOpen) {
            Button("Xóa nhân viên và toàn bộ chấm công", role: .destructive) { model.deleteSelected() }
            Button("Hủy", role: .cancel) {}
        } message: {
            Text("Thao tác này không thể hoàn tác. Hãy xuất CSV trước khi xóa.")
        }
        .alert("Thông báo", isPresented: Binding(
            get: { model.errorMessage != nil },
            set: { if !$0 { model.errorMessage = nil } }
        )) {
            Button("Đóng") { model.errorMessage = nil }
        } message: {
            Text(model.errorMessage ?? "")
        }
    }
    private var employeeSidebar: some View {
        VStack(alignment: .leading, spacing: 14) {
            Label("CHẤM CÔNG", systemImage: "calendar.badge.clock")
                .font(.headline).padding(.top, 7)
            Text("NHÂN VIÊN").font(.caption.bold()).foregroundStyle(.secondary)
            ScrollView {
                VStack(spacing: 5) {
                    ForEach(model.employees) { person in
                        Button {
                            model.selectedID = person.id
                            model.save()
                        } label: {
                            HStack(spacing: 10) {
                                Image(systemName: "person.crop.circle.fill").font(.title3)
                                Text(person.name).lineLimit(1)
                                Spacer(minLength: 0)
                                if model.selectedID == person.id { Image(systemName: "checkmark") }
                            }
                            .padding(10).frame(maxWidth: .infinity, alignment: .leading)
                            .background(model.selectedID == person.id ? Color.blue.opacity(0.15) : Color.clear)
                            .clipShape(RoundedRectangle(cornerRadius: 9))
                        }.buttonStyle(.plain)
                    }
                }
            }
            Divider()
            Button {
                newEmployeeName = ""
                isNewEmployeeOpen = true
            } label: { Label("Thêm nhân viên", systemImage: "plus.circle") }
            Text("Lưu tự động trên máy Mac").font(.caption2).foregroundStyle(.secondary)
        }
        .padding(18).frame(width: 228)
        .background(Color(nsColor: .controlBackgroundColor))
    }
    private var mainPanel: some View {
        VStack(alignment: .leading, spacing: 16) {
            HStack {
                VStack(alignment: .leading, spacing: 4) {
                    Text(model.selected?.name ?? "Chấm công").font(.largeTitle.bold())
                    Text("Chỉ những ngày được đánh dấu mới tính công và lương")
                        .foregroundStyle(.secondary).font(.subheadline)
                }
                Spacer()
                Button { model.exportCSV(for: dates, month: month) } label: {
                    Label("Xuất CSV", systemImage: "square.and.arrow.up")
                }
                Button { openSettings() } label: {
                    Label("Lương & nhân viên", systemImage: "gearshape")
                }
            }
            let summary = model.summary(for: dates)
            HStack(spacing: 10) {
                metric("Ngày đi làm", "\(summary.days) ngày", "calendar.badge.checkmark")
                metric("Giờ làm", String(format: "%.1f giờ", summary.hours), "clock")
                metric("Tăng ca", String(format: "%.1f giờ", summary.overtime), "bolt")
                metric("Lương ước tính", summary.pay.formatted(.currency(code: "JPY").precision(.fractionLength(0))), "yensign.circle")
            }
            HStack(spacing: 10) {
                Button { changeMonth(-1) } label: { Image(systemName: "chevron.left") }
                Text(month.formatted(.dateTime.month(.wide).year()))
                    .font(.title2.bold()).frame(maxWidth: .infinity)
                Button { changeMonth(1) } label: { Image(systemName: "chevron.right") }
                Button("Tháng này") {
                    month = calendar.date(from: calendar.dateComponents([.year, .month], from: Date()))!
                }
            }
            let columns = Array(repeating: GridItem(.flexible(), spacing: 7), count: 7)
            LazyVGrid(columns: columns, spacing: 7) {
                ForEach(["T2", "T3", "T4", "T5", "T6", "T7", "CN"], id: \.self) { label in
                    Text(label).font(.caption.bold()).foregroundStyle(.secondary)
                }
                ForEach(0..<dayOffset, id: \.self) { _ in Color.clear.frame(height: 70) }
                ForEach(dates, id: \.self) { date in dayButton(date) }
            }
            HStack(spacing: 18) {
                Label("Đi làm", systemImage: "checkmark.circle.fill").foregroundStyle(.green)
                Label("Nghỉ", systemImage: "minus.circle.fill").foregroundStyle(.orange)
                Label("Chưa chấm", systemImage: "circle.dashed").foregroundStyle(.secondary)
            }.font(.caption)
            Text("Lương dự kiến = (ngày làm + nghỉ phép hưởng lương) × lương tháng/26 + tiền tăng ca. Chưa trừ thuế, bảo hiểm và các khoản khác.")
                .font(.caption).foregroundStyle(.secondary)
            Spacer(minLength: 0)
        }
        .padding(22)
    }
    private func metric(_ title: String, _ value: String, _ icon: String) -> some View {
        VStack(alignment: .leading, spacing: 8) {
            Label(title, systemImage: icon).font(.caption).foregroundStyle(.secondary)
            Text(value).font(.title3.bold()).minimumScaleFactor(0.7).lineLimit(1)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(12)
        .background(Color(nsColor: .controlBackgroundColor))
        .clipShape(RoundedRectangle(cornerRadius: 10))
    }
    private func dayButton(_ date: Date) -> some View {
        let entry = model.entry(for: date)
        let isToday = calendar.isDateInToday(date)
        let background: Color = entry == nil ? .gray :
            entry!.status == .worked ? .green :
            entry!.status == .paidLeave ? .blue : .orange
        return Button {
            selectedDate = date
            draft = entry ?? WorkEntry()
            isDayEditorOpen = true
        } label: {
            VStack(alignment: .leading, spacing: 6) {
                HStack {
                    Text(date.formatted(.dateTime.day())).font(.headline)
                    Spacer()
                    if isToday { Image(systemName: "circle.fill").font(.system(size: 7)) }
                }
                Text(entry?.status.rawValue ?? "Chưa chấm")
                    .font(.system(size: 10)).lineLimit(1)
                if let entry, entry.status == .worked {
                    Text(String(format: "%.1f giờ", model.hours(entry))).font(.caption2)
                }
                Spacer(minLength: 0)
            }
            .padding(7).frame(maxWidth: .infinity, alignment: .leading).frame(height: 75)
            .background(background.opacity(entry == nil ? 0.055 : 0.12))
            .clipShape(RoundedRectangle(cornerRadius: 8))
            .overlay(RoundedRectangle(cornerRadius: 8).stroke(isToday ? Color.blue : Color.clear, lineWidth: 1.5))
        }.buttonStyle(.plain)
    }
    private var dayEditor: some View {
        Form {
            Text(selectedDate.formatted(date: .complete, time: .omitted)).font(.headline)
            Picker("Trạng thái", selection: $draft.status) {
                ForEach(Attendance.allCases) { status in Text(status.rawValue).tag(status) }
            }
            if draft.status == .worked {
                TextField("Bắt đầu (HH:MM)", text: $draft.start)
                TextField("Kết thúc (HH:MM)", text: $draft.end)
                Stepper("Nghỉ giữa ca: \(draft.breakMinutes) phút", value: $draft.breakMinutes, in: 0...240, step: 15)
                Text("Giờ thực tế: \(model.hours(draft), specifier: "%.1f") giờ")
            }
            TextField("Ghi chú", text: $draft.note)
            HStack {
                Button("Bỏ chấm công ngày này") {
                    model.setEntry(nil, for: selectedDate)
                    isDayEditorOpen = false
                }
                Spacer()
                Button("Hủy") { isDayEditorOpen = false }
                Button("Lưu") {
                    model.setEntry(draft, for: selectedDate)
                    isDayEditorOpen = false
                }
                .buttonStyle(.borderedProminent)
                .disabled(draft.status == .worked && !validTime(draft.start, draft.end))
            }
        }
        .padding(22).frame(width: 460)
    }
    private func validTime(_ a: String, _ b: String) -> Bool {
        func valid(_ s: String) -> Bool {
            let v = s.split(separator: ":").compactMap { Int($0) }
            return v.count == 2 && (0...23).contains(v[0]) && (0...59).contains(v[1])
        }
        return valid(a) && valid(b) && a != b
    }
    private func openSettings() {
        guard let employee = model.selected else { return }
        editName = employee.name
        editSalary = employee.monthlySalary
        editDays = employee.standardDays
        editHours = employee.standardHours
        editMultiplier = employee.overtimeMultiplier
        isSettingsOpen = true
    }
    private var settingsSheet: some View {
        Form {
            Text("Thiết lập nhân viên và tiền lương").font(.title2.bold())
            TextField("Tên nhân viên", text: $editName)
            HStack { Text("Lương cơ bản (¥/tháng)"); Spacer(); TextField("Yên", value: $editSalary, format: .number).frame(width: 130) }
            Stepper("Ngày công chuẩn: \(editDays) ngày", value: $editDays, in: 1...31)
            HStack { Text("Giờ làm chuẩn/ngày"); Spacer(); TextField("Giờ", value: $editHours, format: .number).frame(width: 100) }
            HStack { Text("Hệ số tăng ca"); Spacer(); TextField("Hệ số", value: $editMultiplier, format: .number).frame(width: 100) }
            Text("Mặc định: 205.000 ¥ / 26 ngày, 8 giờ/ngày, tăng ca ×1,25.")
                .font(.caption).foregroundStyle(.secondary)
            HStack {
                Button("Xóa nhân viên", role: .destructive) {
                    isSettingsOpen = false
                    isDeleteConfirmationOpen = true
                }.disabled(model.employees.count < 2)
                Spacer()
                Button("Hủy") { isSettingsOpen = false }
                Button("Lưu") {
                    model.updateEmployee(name: editName, salary: editSalary, days: editDays,
                                         hours: editHours, multiplier: editMultiplier)
                    if model.errorMessage == nil { isSettingsOpen = false }
                }.buttonStyle(.borderedProminent)
            }
        }
        .padding(24).frame(width: 490)
    }
    private func changeMonth(_ value: Int) {
        if let next = calendar.date(byAdding: .month, value: value, to: month) { month = next }
    }
}
@main struct ChamCongMacApp: App {
    var body: some Scene { WindowGroup { ContentView() } }
}
