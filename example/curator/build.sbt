name         := "kazoorator"
organization := "com.pseudomuto.kazoorator"
version      := "0.1.0"
scalaVersion := "2.11.8"

assemblyJarName    := "curator.jar"

libraryDependencies ++= Seq(
  "org.apache.curator" % "curator-recipes" % "2.11.0"
)
