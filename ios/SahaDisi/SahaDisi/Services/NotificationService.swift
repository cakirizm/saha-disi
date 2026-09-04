import Foundation
import Combine
import UserNotifications

@MainActor
final class NotificationService: ObservableObject {
    static let shared = NotificationService()

    @Published private(set) var allEnabled: Bool
    @Published private(set) var commentatorIDs: Set<String>
    @Published private(set) var teamNames: Set<String>
    @Published private(set) var commentatorTeamKeys: Set<String>

    private let allKey = "sahadisi.notifications.all"
    private let commentatorsKey = "sahadisi.notifications.commentators"
    private let teamsKey = "sahadisi.notifications.teams"
    private let pairsKey = "sahadisi.notifications.commentatorTeams"

    private init() {
        let defaults = UserDefaults.standard
        allEnabled = defaults.bool(forKey: allKey)
        commentatorIDs = Set(defaults.stringArray(forKey: commentatorsKey) ?? [])
        teamNames = Set(defaults.stringArray(forKey: teamsKey) ?? [])
        commentatorTeamKeys = Set(defaults.stringArray(forKey: pairsKey) ?? [])
    }

    func requestPermission() async -> Bool {
        do {
            return try await UNUserNotificationCenter.current().requestAuthorization(options: [.alert, .badge, .sound])
        } catch {
            return false
        }
    }

    func setAll(_ enabled: Bool) async {
        if enabled && !(await requestPermission()) { return }
        allEnabled = enabled
        UserDefaults.standard.set(enabled, forKey: allKey)
    }

    func toggleCommentator(_ id: String) async {
        if !commentatorIDs.contains(id) && !(await requestPermission()) { return }
        if commentatorIDs.contains(id) { commentatorIDs.remove(id) } else { commentatorIDs.insert(id) }
        persist(commentatorIDs, key: commentatorsKey)
    }

    func toggleTeam(_ team: String) async {
        if !teamNames.contains(team) && !(await requestPermission()) { return }
        if teamNames.contains(team) { teamNames.remove(team) } else { teamNames.insert(team) }
        persist(teamNames, key: teamsKey)
    }

    func toggle(commentatorID: String, team: String) async {
        let key = pairKey(commentatorID, team)
        if !commentatorTeamKeys.contains(key) && !(await requestPermission()) { return }
        if commentatorTeamKeys.contains(key) { commentatorTeamKeys.remove(key) } else { commentatorTeamKeys.insert(key) }
        persist(commentatorTeamKeys, key: pairsKey)
    }

    func isCommentatorEnabled(_ id: String) -> Bool { commentatorIDs.contains(id) }
    func isTeamEnabled(_ team: String) -> Bool { teamNames.contains(team) }
    func isPairEnabled(_ commentatorID: String, team: String) -> Bool { commentatorTeamKeys.contains(pairKey(commentatorID, team)) }

    func deliverNewStatements(_ statements: [Statement], commentators: [Commentator]) async {
        guard !statements.isEmpty else { return }
        let names = Dictionary(uniqueKeysWithValues: commentators.map { ($0.id, $0.name) })
        for statement in statements.prefix(12) where shouldNotify(statement) {
            let content = UNMutableNotificationContent()
            content.title = names[statement.commentator] ?? "Saha Dışı"
            content.body = statement.summary
            content.sound = .default
            content.userInfo = ["statement_id": statement.id]
            let request = UNNotificationRequest(identifier: "statement-\(statement.id)", content: content, trigger: nil)
            try? await UNUserNotificationCenter.current().add(request)
        }
    }

    private func shouldNotify(_ statement: Statement) -> Bool {
        if allEnabled { return true }
        if commentatorIDs.contains(statement.commentator) { return true }
        if let team = statement.team, teamNames.contains(team) { return true }
        if let team = statement.team, commentatorTeamKeys.contains(pairKey(statement.commentator, team)) { return true }
        return false
    }

    private func pairKey(_ commentatorID: String, _ team: String) -> String { "\(commentatorID)|\(team)" }
    private func persist(_ values: Set<String>, key: String) { UserDefaults.standard.set(Array(values).sorted(), forKey: key) }
}
