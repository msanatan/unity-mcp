using System;
using System.Collections.Generic;
using System.Linq;
using System.Reflection;
using MCPForUnity.Editor.Services.Transport.Transports;
using NUnit.Framework;

namespace MCPForUnityTests.Editor.Services
{
    [TestFixture]
    public class WebSocketTransportClientTests
    {
        private static readonly MethodInfo BuildConnectionCandidateUrisMethod =
            typeof(WebSocketTransportClient).GetMethod(
                "BuildConnectionCandidateUris",
                BindingFlags.NonPublic | BindingFlags.Static);

        [Test]
        public void BuildConnectionCandidateUris_NullEndpoint_ReturnsEmptyList()
        {
            // Act
            List<Uri> candidates = InvokeBuildConnectionCandidateUris(null);

            // Assert
            Assert.IsNotNull(candidates);
            Assert.AreEqual(0, candidates.Count);
        }

        [Test]
        public void BuildConnectionCandidateUris_NonLocalhost_ReturnsOriginalOnly()
        {
            // Arrange
            var endpoint = new Uri("ws://127.0.0.1:8080/hub/plugin");

            // Act
            List<Uri> candidates = InvokeBuildConnectionCandidateUris(endpoint);

            // Assert
            Assert.AreEqual(1, candidates.Count);
            Assert.AreEqual(endpoint, candidates[0]);
        }

        [Test]
        public void BuildConnectionCandidateUris_Localhost_AddsIPv4AndIPv6Fallbacks()
        {
            // Arrange
            var endpoint = new Uri("ws://localhost:8080/hub/plugin");

            // Act
            List<Uri> candidates = InvokeBuildConnectionCandidateUris(endpoint);

            // Assert
            Assert.AreEqual(3, candidates.Count);
            CollectionAssert.AreEqual(
                new[] { "localhost", "127.0.0.1", "::1" },
                candidates.Select(uri => uri.Host).ToArray());

            int uniqueCount = candidates
                .Select(uri => uri.AbsoluteUri)
                .Distinct(StringComparer.OrdinalIgnoreCase)
                .Count();
            Assert.AreEqual(candidates.Count, uniqueCount, "Fallback list should not contain duplicate endpoints.");
        }

        [Test]
        public void BuildConnectionCandidateUris_LocalhostFallbacks_PreserveSchemePortPathAndQuery()
        {
            // Arrange
            var endpoint = new Uri("wss://localhost:9443/custom/path?mode=test");

            // Act
            List<Uri> candidates = InvokeBuildConnectionCandidateUris(endpoint);

            // Assert
            Assert.AreEqual(3, candidates.Count);
            foreach (Uri candidate in candidates)
            {
                Assert.AreEqual("wss", candidate.Scheme);
                Assert.AreEqual(9443, candidate.Port);
                Assert.AreEqual("/custom/path", candidate.AbsolutePath);
                Assert.AreEqual("?mode=test", candidate.Query);
            }
        }

        private static List<Uri> InvokeBuildConnectionCandidateUris(Uri endpoint)
        {
            Assert.IsNotNull(BuildConnectionCandidateUrisMethod, "Expected private candidate builder method to exist.");
            var result = BuildConnectionCandidateUrisMethod.Invoke(null, new object[] { endpoint });
            Assert.IsNotNull(result);
            Assert.IsInstanceOf<List<Uri>>(result);
            return (List<Uri>)result;
        }
    }
}
