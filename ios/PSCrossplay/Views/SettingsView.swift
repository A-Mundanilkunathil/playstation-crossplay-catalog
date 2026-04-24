import SwiftUI

struct SettingsView: View {
    @Environment(\.dismiss) private var dismiss
    @State private var token: String = ""
    @State private var hasToken: Bool = KeychainPAT.load() != nil

    var body: some View {
        NavigationStack {
            Form {
                Section {
                    if hasToken {
                        Label("Token saved in Keychain", systemImage: "checkmark.shield.fill")
                            .foregroundStyle(.green)
                        Button(role: .destructive) {
                            KeychainPAT.delete()
                            hasToken = false
                            token = ""
                        } label: {
                            Label("Remove token", systemImage: "trash")
                        }
                    } else {
                        SecureField("ghp_…", text: $token)
                        Button {
                            let trimmed = token.trimmingCharacters(in: .whitespacesAndNewlines)
                            guard !trimmed.isEmpty else { return }
                            KeychainPAT.save(trimmed)
                            hasToken = true
                            token = ""
                        } label: {
                            Label("Save token", systemImage: "lock.shield")
                        }
                        .disabled(token.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty)
                    }
                } header: {
                    Text("GitHub token")
                } footer: {
                    Text("Needed only for the \"Rebuild now\" button. Create a fine-grained PAT with Actions: Read & Write scope on the playstation-crossplay-catalog repo at github.com/settings/tokens. Stored in iOS Keychain, device-only.")
                }

                Section {
                    LinkRow(title: "Source code", url: "https://github.com/A-Mundanilkunathil/playstation-crossplay-catalog")
                    LinkRow(title: "Public catalog JSON", url: GameStore.gamesURL.absoluteString)
                } header: {
                    Text("About")
                }
            }
            .navigationTitle("Settings")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    Button("Done") { dismiss() }
                }
            }
        }
    }
}

private struct LinkRow: View {
    let title: String
    let url: String
    var body: some View {
        if let u = URL(string: url) {
            Link(destination: u) {
                HStack {
                    Text(title)
                    Spacer()
                    Image(systemName: "arrow.up.right.square")
                        .foregroundStyle(.secondary)
                }
            }
        }
    }
}
