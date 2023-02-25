/*
([system.reflection.assembly]::loadfile("AppData\Roaming\Sublime Text 3\Packages\se-mdk\lib\System.Collections.Immutable.dll")).FullName
([system.reflection.assembly]::loadfile("AppData\Roaming\Sublime Text 3\Packages\se-mdk\lib\Microsoft.CodeAnalysis.dll")).FullName
*/
using System.IO;
using System.Linq;
using System.Text.RegularExpressions;
using Microsoft.CodeAnalysis;
using Microsoft.CodeAnalysis.CSharp;
using Microsoft.CodeAnalysis.CSharp.Syntax;

namespace mdkmin {
    class Minifier {
        class TriviaTrimmer : CSharpSyntaxRewriter {
            public TriviaTrimmer() : base(true) { }

            public override SyntaxTrivia VisitTrivia(SyntaxTrivia trivia) {
                // skip if it's a random trailing brace (https://github.com/malware-dev/MDK-SE/wiki/Utility-Class-or-Extension-Class)
                if (trivia.ToFullString().Trim() == "}") {
                    return trivia;
                }
                return default(SyntaxTrivia);
            }
        }

        class SyntaxTrimmer : CSharpSyntaxRewriter {
            public override SyntaxNode VisitFieldDeclaration(FieldDeclarationSyntax node) {
                var changed = base.VisitFieldDeclaration(node);
                var modifiers = node.Modifiers.Select(m => m.Kind()).ToList();
                if (modifiers.Remove(SyntaxKind.ReadOnlyKeyword)) {
                    return node.WithModifiers(SyntaxFactory.TokenList(modifiers.Select(SyntaxFactory.Token).ToArray()));
                }

                return changed;
            }
        }

        SyntaxNode TrimTrivia(SyntaxNode root) {
            var triviaTrimmer = new TriviaTrimmer();
            root = triviaTrimmer.Visit(root);
            root = root.NormalizeWhitespace("", "\n", true);

            return root;
        }

        SyntaxNode TrimSyntax(SyntaxNode root) {
            var trimmer = new SyntaxTrimmer();

            return trimmer.Visit(root);
        }

        public string Minify(string filepath) {
            string source = File.ReadAllText(filepath);
            SyntaxTree tree = CSharpSyntaxTree.ParseText(source);
            SyntaxNode root = tree.GetRoot();

            root = this.TrimSyntax(root);
            root = this.TrimTrivia(root);

            return this.RemoveWhitespace(root.ToFullString());
        }

        public string RemoveWhitespace(string script) {
            var regex = new Regex(@"(?<string>\$?((@""[^""]*(""""[^""]*)*"")|(""[^""\\\r\n]*(?:\\.[^""\\\r\n]*)*"")|('[^'\\\r\n]*(?:\\.[^'\\\r\n]*)*')))|(?<significant>\b\s+\b)|(?<insignificant>\s+)", RegexOptions.IgnoreCase | RegexOptions.Singleline | RegexOptions.ExplicitCapture);
            int lastNewlineIndex = 0;
            int indexOffset = 0;

            return  regex.Replace(script, match => {
                if (match.Groups["string"].Success) {
                    return match.Value;
                }

                var index = match.Index + indexOffset;
                if (index - lastNewlineIndex > 200) {
                    indexOffset -= match.Length - 1;
                    lastNewlineIndex = index;

                    return "\n";
                }

                if (match.Groups["significant"].Success) {
                    indexOffset -= match.Length - 1;

                    return " ";
                }
                indexOffset -= match.Length;

                return "";
            });
        }
    }

    class Program {
        static void Main(string[] args) {
            Minifier minifier = new Minifier();
            string minified = minifier.Minify(args[0]);

            File.WriteAllText(args[1], minified);
        }
    }
}
