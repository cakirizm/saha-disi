import SwiftUI

extension Font {
    func black() -> Font { weight(.black) }
}

enum SDTheme {
    static let background = Color(red: 0.020, green: 0.040, blue: 0.055)
    static let background2 = Color(red: 0.030, green: 0.058, blue: 0.075)
    static let panel = Color(red: 0.045, green: 0.078, blue: 0.096)
    static let panel2 = Color(red: 0.065, green: 0.105, blue: 0.125)
    static let line = Color.white.opacity(0.08)
    static let accent = Color(red: 0.22, green: 0.54, blue: 0.98)
    static let green = Color(red: 0.24, green: 0.84, blue: 0.55)
    static let red = Color(red: 0.96, green: 0.26, blue: 0.31)
    static let muted = Color.white.opacity(0.60)
    static let muted2 = Color.white.opacity(0.38)
}

enum SDDate {
    private static let tr: DateFormatter = {
        let f = DateFormatter(); f.locale = Locale(identifier: "tr_TR"); f.dateFormat = "d MMMM yyyy"; return f
    }()
    private static let trTime: DateFormatter = {
        let f = DateFormatter(); f.locale = Locale(identifier: "tr_TR"); f.dateFormat = "d MMMM yyyy · HH:mm"; return f
    }()
    private static let iso = ISO8601DateFormatter()
    private static let simple: DateFormatter = {
        let f = DateFormatter(); f.locale = Locale(identifier: "en_US_POSIX"); f.dateFormat = "yyyy-MM-dd"; return f
    }()
    private static let tff: DateFormatter = {
        let f = DateFormatter(); f.locale = Locale(identifier: "tr_TR"); f.dateFormat = "dd.MM.yyyy HH:mm"; return f
    }()

    static func text(_ value: String, includeTime: Bool = false) -> String {
        guard !value.isEmpty else { return "Tarih açıklanmadı" }
        let date = iso.date(from: value) ?? simple.date(from: value) ?? tff.date(from: value)
        guard let date else { return value }
        return (includeTime ? trTime : tr).string(from: date)
    }
}

struct SDCard<Content: View>: View {
    @ViewBuilder var content: () -> Content
    var body: some View {
        content().padding(16).background(SDTheme.panel)
            .clipShape(RoundedRectangle(cornerRadius: 17, style: .continuous))
            .overlay(RoundedRectangle(cornerRadius: 17).stroke(SDTheme.line))
    }
}

struct SDMark: View {
    var size: CGFloat = 38
    var body: some View {
        ZStack(alignment: .bottomLeading) {
            RoundedRectangle(cornerRadius: size * 0.22, style: .continuous).fill(Color.white).frame(width: size, height: size * 0.78)
            Path { p in
                p.move(to: CGPoint(x: size * 0.14, y: size * 0.65)); p.addLine(to: CGPoint(x: size * 0.04, y: size * 0.96)); p.addLine(to: CGPoint(x: size * 0.34, y: size * 0.74)); p.closeSubpath()
            }.fill(Color.white)
            ZStack {
                RoundedRectangle(cornerRadius: size * 0.09).stroke(SDTheme.background, lineWidth: max(1.5, size * 0.055))
                Rectangle().fill(SDTheme.background).frame(width: max(1.5, size * 0.05))
                Circle().stroke(SDTheme.background, lineWidth: max(1.3, size * 0.045)).frame(width: size * 0.20, height: size * 0.20)
                HStack { RoundedRectangle(cornerRadius: 2).stroke(SDTheme.background, lineWidth: max(1.2, size * 0.04)).frame(width: size * 0.13, height: size * 0.24); Spacer(); RoundedRectangle(cornerRadius: 2).stroke(SDTheme.background, lineWidth: max(1.2, size * 0.04)).frame(width: size * 0.13, height: size * 0.24) }
            }.padding(size * 0.12).frame(width: size, height: size * 0.63).offset(y: size * 0.03)
            HStack(spacing: size * 0.07) { Circle(); Circle(); Circle() }.foregroundStyle(SDTheme.background).frame(width: size * 0.26, height: size * 0.04).offset(x: size * 0.37, y: -size * 0.06)
        }.frame(width: size, height: size)
    }
}

struct AvatarView: View {
    let text: String
    let size: CGFloat
    var photoURL: String? = nil
    var body: some View {
        ZStack {
            Circle().fill(LinearGradient(colors: [SDTheme.panel2, SDTheme.background2], startPoint: .topLeading, endPoint: .bottomTrailing))
            Text(text).font(.system(size: size * 0.28, weight: .black, design: .rounded))
            if let photoURL, let url = URL(string: photoURL) {
                AsyncImage(url: url) { phase in if case .success(let image) = phase { image.resizable().scaledToFill() } }
            }
        }.frame(width: size, height: size).clipShape(Circle()).overlay(Circle().stroke(Color.white.opacity(0.12)))
    }
}

struct TeamLogoView: View {
    let name: String
    var urlString: String? = nil
    var size: CGFloat = 58
    var body: some View {
        ZStack {
            Circle().fill(Color.white.opacity(0.05))
            if let urlString, let url = URL(string: urlString) {
                AsyncImage(url: url) { phase in
                    if case .success(let image) = phase { image.resizable().scaledToFit().padding(size * 0.12) }
                    else { fallback }
                }
            } else { fallback }
        }.frame(width: size, height: size).overlay(Circle().stroke(Color.white.opacity(0.10)))
    }
    private var fallback: some View {
        Text(String(name.split(separator: " ").prefix(2).compactMap { $0.first }.map(String.init).joined()))
            .font(.system(size: size * 0.30, weight: .black, design: .rounded))
    }
}

struct TagPill: View {
    let text: String
    var highlighted: Bool = false
    var body: some View {
        Text(text).font(.caption2.weight(.semibold)).padding(.horizontal, 9).padding(.vertical, 5)
            .foregroundStyle(highlighted ? .white : SDTheme.muted)
            .background(highlighted ? SDTheme.accent : Color.white.opacity(0.06)).clipShape(Capsule())
    }
}

struct SDLogo: View {
    var compact = false
    var body: some View {
        Text("Saha Dışı").font(.system(size: compact ? 20 : 27, weight: .black, design: .rounded)).tracking(-0.5)
    }
}

struct RankBar: View {
    let rank: Int; let name: String; let count: Int; let maxCount: Int
    var body: some View {
        HStack(spacing: 10) {
            Text("\(rank)").font(.subheadline.bold()).foregroundStyle(SDTheme.muted).frame(width: 20)
            Text(name).font(.subheadline.weight(.semibold)).lineLimit(1).frame(width: 120, alignment: .leading)
            GeometryReader { proxy in Capsule().fill(Color.white.opacity(0.06)).overlay(alignment: .leading) { Capsule().fill(SDTheme.accent).frame(width: max(8, proxy.size.width * CGFloat(count) / CGFloat(max(1, maxCount)))) } }.frame(height: 6)
            Text("\(count)").font(.subheadline.bold()).frame(width: 28, alignment: .trailing)
        }.frame(height: 28)
    }
}
