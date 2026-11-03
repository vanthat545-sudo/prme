import SwiftUI
import Foundation

struct Shift: Codable {
    var start = "08:00"
    var end = "17:00"
    var breakMinutes = 60
    var off = false
    var note = ""
}
@MainActor final class Timesheet: ObservableObject {
    @Published var shifts: [String:Shift] = [:]
    @Published var rate: Double = 1200
    @Published var multiplier: Double = 1.25
    struct DataFile: Codable { var shifts: [String:Shift]; var rate: Double; var multiplier: Double }
    let url = FileManager.default.homeDirectoryForCurrentUser.appendingPathComponent("Library/Application Support/ChamCongMac/data.json")
    init() {
        if let data = try? Data(contentsOf: url), let d = try? JSONDecoder().decode(DataFile.self,from:data) {
            shifts=d.shifts;rate=d.rate;multiplier=d.multiplier
        }
    }
    func save() {
        try? FileManager.default.createDirectory(at:url.deletingLastPathComponent(),withIntermediateDirectories:true)
        if let data=try? JSONEncoder().encode(DataFile(shifts:shifts,rate:rate,multiplier:multiplier)) {
            try? data.write(to:url,options:.atomic)
        }
    }
    func key(_ date:Date)->String { date.formatted(.iso8601.year().month().day().dateSeparator(.dash)) }
    func shift(_ date:Date)->Shift { shifts[key(date)] ?? Shift(off:Calendar.current.component(.weekday,from:date)==1) }
    func hours(_ s:Shift)->Double {
        if s.off{return 0}
        func minutes(_ t:String)->Int? {
            let a=t.split(separator:":").compactMap{Int($0)}
            guard a.count==2,(0...23).contains(a[0]),(0...59).contains(a[1]) else{return nil}
            return a[0]*60+a[1]
        }
        guard let a=minutes(s.start),let b=minutes(s.end) else{return 0}
        return Double(max(0,(b>a ? b-a : b+1440-a)-max(0,s.breakMinutes)))/60
    }
}
struct ContentView: View {
    @StateObject var model=Timesheet()
    @State var month=Calendar.current.date(from:Calendar.current.dateComponents([.year,.month],from:Date()))!
    @State var chosen=Date()
    @State var draft=Shift()
    @State var editor=false
    @State var settings=false
    let cal=Calendar.current
    var dates:[Date] {
        guard let r=cal.range(of:.day,in:.month,for:month) else{return []}
        return r.compactMap{cal.date(byAdding:.day,value:$0-1,to:month)}
    }
    var total:Double {dates.reduce(0){$0+model.hours(model.shift($1))}}
    var overtime:Double {dates.reduce(0){$0+max(0,model.hours(model.shift($1))-8)}}
    var pay:Double {(total-overtime)*model.rate+overtime*model.rate*model.multiplier}
    var body:some View {
        VStack(alignment:.leading,spacing:18) {
            HStack {
                VStack(alignment:.leading) {
                    Text("CHẤM CÔNG MAC").font(.largeTitle.bold())
                    Text("Lịch làm việc tại Nhật Bản • Dữ liệu lưu ngoại tuyến").foregroundStyle(.secondary)
                }
                Spacer()
                Button("Cài đặt lương"){settings=true}
            }
            HStack(spacing:14) {
                metric("Giờ làm",String(format:"%.1f giờ",total),"clock")
                metric("Tăng ca",String(format:"%.1f giờ",overtime),"bolt")
                metric("Lương dự kiến",String(format:"¥%.0f",pay),"yensign.circle")
            }
            HStack {
                Button {month=cal.date(byAdding:.month,value:-1,to:month)!} label:{Image(systemName:"chevron.left")}
                Text(month.formatted(.dateTime.month(.wide).year())).font(.title2.bold()).frame(maxWidth:.infinity)
                Button {month=cal.date(byAdding:.month,value:1,to:month)!} label:{Image(systemName:"chevron.right")}
                Button("Hôm nay"){month=cal.date(from:cal.dateComponents([.year,.month],from:Date()))!}
            }
            let columns=Array(repeating:GridItem(.flexible(),spacing:8),count:7)
            LazyVGrid(columns:columns,spacing:8) {
                ForEach(["T2","T3","T4","T5","T6","T7","CN"],id:\.self){Text($0).font(.caption.bold()).foregroundStyle(.secondary)}
                ForEach(0..<((cal.component(.weekday,from:month)+5)%7),id:\.self){_ in Color.clear.frame(height:70)}
                ForEach(dates,id:\.self){day in
                    let s=model.shift(day)
                    Button {
                        chosen=day;draft=s;editor=true
                    } label:{
                        VStack(alignment:.leading,spacing:8){
                            Text(day.formatted(.dateTime.day())).font(.headline)
                            Text(s.off ? "Nghỉ" : String(format:"%.1f giờ",model.hours(s)))
                                .font(.caption)
                                .foregroundStyle(s.off ? .red : .secondary)
                            Spacer(minLength:0)
                        }
                        .frame(maxWidth:.infinity,alignment:.leading).frame(height:64)
                        .padding(8)
                        .background(s.off ? Color.red.opacity(0.08) : Color.blue.opacity(0.07))
                        .clipShape(RoundedRectangle(cornerRadius:12))
                    }.buttonStyle(.plain)
                }
            }
            Text("Chọn một ngày để nhập giờ làm, giờ nghỉ và ghi chú. Chủ nhật mặc định nghỉ.").foregroundStyle(.secondary).font(.caption)
            Spacer(minLength:0)
        }
        .padding(24).frame(minWidth:900,minHeight:690)
        .sheet(isPresented:$editor){
            Form {
                Text(chosen.formatted(date:.complete,time:.omitted)).font(.headline)
                Toggle("Ngày nghỉ",isOn:$draft.off)
                TextField("Giờ bắt đầu (HH:MM)",text:$draft.start)
                TextField("Giờ kết thúc (HH:MM)",text:$draft.end)
                Stepper("Nghỉ giữa ca: \(draft.breakMinutes) phút",value:$draft.breakMinutes,in:0...240,step:15)
                TextField("Ghi chú",text:$draft.note)
                HStack {
                    Button("Hủy"){editor=false}
                    Spacer()
                    Button("Lưu"){
                        model.shifts[model.key(chosen)]=draft
                        model.save();editor=false
                    }.buttonStyle(.borderedProminent)
                }
            }.padding(24).frame(width:430)
        }
        .sheet(isPresented:$settings){
            Form {
                Text("Thiết lập tiền lương").font(.headline)
                HStack {Text("Lương mỗi giờ (¥)");TextField("JPY",value:$model.rate,format:.number).frame(width:110)}
                HStack {Text("Hệ số tăng ca");TextField("Hệ số",value:$model.multiplier,format:.number).frame(width:110)}
                Button("Lưu cài đặt"){model.save();settings=false}.buttonStyle(.borderedProminent)
            }.padding(24).frame(width:380)
        }
    }
    func metric(_ label:String,_ value:String,_ icon:String)->some View {
        VStack(alignment:.leading,spacing:9){
            Label(label,systemImage:icon).foregroundStyle(.secondary)
            Text(value).font(.title2.bold())
        }.frame(maxWidth:.infinity,alignment:.leading).padding(18)
            .background(.quaternary.opacity(0.5)).clipShape(RoundedRectangle(cornerRadius:14))
    }
}
@main struct ChamCongMacApp:App {
    var body:some Scene {WindowGroup {ContentView()}}
}
