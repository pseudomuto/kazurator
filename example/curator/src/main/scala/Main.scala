package com.pseudomuto.kazoorator

import java.lang.IllegalMonitorStateException
import org.apache.curator.framework.recipes.locks.{InterProcessMutex, InterProcessReadWriteLock}
import org.apache.curator.framework.{CuratorFramework, CuratorFrameworkFactory}
import org.apache.curator.retry.RetryOneTime
import org.slf4j.LoggerFactory
import scala.collection.JavaConversions._
import scala.io.StdIn
import scala.util.control.Breaks._
import scala.util.Properties

object Main {
  final private[this] val CONNECT_STRING = Properties.envOrElse("ZK_CONNECT_STRING", "localhost:2181")
  final private[this] val LOCK_PATH      = "/haderp/some_path"
  final private[this] val LOG            = LoggerFactory.getLogger(getClass)

  def main(args: Array[String]) {
    val client    = createClient
    val lock      = new InterProcessReadWriteLock(client, LOCK_PATH)
    val readLock  = lock.readLock
    val writeLock = lock.writeLock

    breakable {
      while(true) {
        printMenu

        getChoice match {
          case 1 => pad { acquire("READ", readLock) }
          case 2 => pad { acquire("WRITE", writeLock) }
          case 3 => pad { release("READ", readLock) }
          case 4 => pad { release("WRITE", writeLock) }
          case 5 => pad { listNodes(lock) }
          case _ => {
            client.close
            LOG.info("Client closed")
            break
          }
        }
      }
    }
  }

  private[this] def getChoice(): Int = {
    var choice = -1

    try { choice = StdIn.readInt }
    catch { case _: Throwable => }

    choice
  }

  private[this] def colored(input: String, color: String): String = {
    s"$color$input${Console.RESET}"
  }

  private[this] def acquire(name: String, lock: InterProcessMutex): Unit = {
    lock.acquire
    println(colored(s"Acquired the $name lock", Console.GREEN))
  }

  private[this] def release(name: String, lock: InterProcessMutex): Unit = {
    try {
      lock.release
      println(colored(s"Released the $name lock", Console.YELLOW))
    } catch {
      case e: IllegalMonitorStateException => println(colored(s"Whoops!: $e", Console.RED))
    }
  }

  private[this] def createClient(): CuratorFramework = {
    val client = CuratorFrameworkFactory
      .builder
      .retryPolicy(new RetryOneTime(100))
      .connectString(CONNECT_STRING)
      .build

    client.start
    client
  }

  private[this] def listNodes(lock: InterProcessReadWriteLock): Unit = {
    val nodes = lock.readLock.getParticipantNodes ++ lock.writeLock.getParticipantNodes

    println(s"There are ${colored(nodes.size.toString, Console.YELLOW)} node(s) participating:")
    nodes.foreach({ node => println(s"  * $node") })
  }

  private[this] def printMenu(): Unit = {
    println("Select one of the following:")
    println("1. Acquire read lock")
    println("2. Acquire write lock")
    println("3. Release read lock")
    println("4. Release write lock")
    println("5. List participant nodes")
    println("6. Quit")

    print("\nChoice: ")
  }

  private[this] def pad(fn: => Any): Unit = {
    println("\n")
    fn
    println("\n")
  }
}
